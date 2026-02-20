const { spawn } = require('child_process');
const path = require('path');

/**
 * Service to handle execution of AI Python scripts.
 * Centralizes script execution, error handling, and path management.
 */
class AiService {
    constructor() {
        this.aiUtilsPath = path.join(__dirname, '../utils/ai');
        this.rootPath = path.join(__dirname, '../'); // For ai_service.py in root
    }

    /**
     * Executes a Python script with JSON input and returns JSON output.
     * @param {string} scriptName - Name of the script (e.g., 'market_intelligence.py')
     * @param {object} inputData - JSON object to pass to the script via stdin
     * @param {string} [customPath] - Optional custom path if script is not in utils/ai
     * @returns {Promise<object>} - Parsed JSON result
     */
    async executeScript(scriptName, inputData, customPath = null) {
        return new Promise((resolve, reject) => {
            let scriptPath;

            // Determine script location
            if (customPath) {
                scriptPath = path.join(customPath, scriptName);
            } else if (scriptName === 'ai_service.py') {
                // Special case for the legacy root script
                scriptPath = path.join(this.rootPath, scriptName);
            } else {
                // Default to utils/ai directory
                scriptPath = path.join(this.aiUtilsPath, scriptName);
            }

            console.log(`[AiService] Executing: ${scriptName}`);

            const pythonProcess = spawn('python', [scriptPath]);

            let outputString = '';
            let errorString = '';

            // Handle process communication
            try {
                if (inputData) {
                    pythonProcess.stdin.write(JSON.stringify(inputData));
                    pythonProcess.stdin.end();
                }
            } catch (err) {
                return reject(new Error(`Failed to write to stdin of ${scriptName}: ${err.message}`));
            }

            pythonProcess.stdout.on('data', (data) => {
                outputString += data.toString();
            });

            pythonProcess.stderr.on('data', (data) => {
                errorString += data.toString();
            });

            pythonProcess.on('close', (code) => {
                if (code !== 0) {
                    console.error(`[AiService] Error in ${scriptName}: ${errorString}`);
                    // return resolve(null); // Optional: Resolve null instead of rejecting for graceful failure
                    return reject(new Error(`Script ${scriptName} exited with code ${code}. Error: ${errorString}`));
                }

                try {
                    // Attempt to find JSON in the output (handling potential noise)
                    // Sometimes scripts print debug info before the JSON
                    const jsonStartIndex = outputString.indexOf('{');
                    const jsonEndIndex = outputString.lastIndexOf('}');

                    if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
                        const jsonStr = outputString.substring(jsonStartIndex, jsonEndIndex + 1);
                        const result = JSON.parse(jsonStr);
                        resolve(result);
                    } else {
                        // If no JSON found, but no error code, return raw output or empty logic check
                        if (!outputString.trim()) {
                            resolve(null);
                        } else {
                            // Try parsing the whole string just in case
                            resolve(JSON.parse(outputString));
                        }
                    }
                } catch (parseError) {
                    console.error(`[AiService] JSON Parse Error for ${scriptName}:`, parseError);
                    console.error(`[AiService] Raw Output:`, outputString);
                    reject(new Error(`Failed to parse output from ${scriptName}`));
                }
            });

            // Timeout safety (30 seconds)
            setTimeout(() => {
                pythonProcess.kill();
                reject(new Error(`Script ${scriptName} timed out after 30s`));
            }, 30000);
        });
    }
}

module.exports = new AiService();
