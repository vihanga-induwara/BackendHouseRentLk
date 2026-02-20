const mongoose = require('mongoose');

const sessionSchema = mongoose.Schema(
    {
        userId: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'User',
            required: true
        },
        ipAddress: {
            type: String
        },
        userAgent: {
            type: String
        },
        os: {
            type: String // e.g., "Windows 10", "macOS", "Android 12", "iOS 15"
        },
        deviceType: {
            type: String,
            enum: ['mobile', 'tablet', 'desktop', 'unknown'],
            default: 'unknown'
        },
        browser: {
            type: String // e.g., "Chrome 120", "Firefox 115", "Safari 17"
        },
        loginAt: {
            type: Date,
            default: Date.now
        },
        logoutAt: {
            type: Date
        }
    },
    {
        timestamps: true
    }
);

// Index for security queries
sessionSchema.index({ userId: 1, loginAt: -1 });

module.exports = mongoose.model('Session', sessionSchema);

