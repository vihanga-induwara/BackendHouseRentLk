const UAParser = require('ua-parser-js');

/**
 * Parse user agent string to extract device details
 * @param {string} userAgentString - The user agent string from request headers
 * @returns {object} Parsed device information
 */
const parseUserAgent = (userAgentString) => {
    const parser = new UAParser(userAgentString);
    const result = parser.getResult();

    return {
        browser: `${result.browser.name || 'Unknown'} ${result.browser.version || ''}`.trim(),
        os: `${result.os.name || 'Unknown'} ${result.os.version || ''}`.trim(),
        deviceType: result.device.type || 'desktop', // mobile, tablet, or desktop (default)
        userAgent: userAgentString
    };
};

module.exports = { parseUserAgent };
