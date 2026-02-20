const mongoose = require('mongoose');

const scrapingSourceSchema = mongoose.Schema(
    {
        name: {
            type: String,
            required: [true, 'Please add a source name'],
            trim: true,
        },
        slug: {
            type: String,
            required: true,
            unique: true,
            lowercase: true,
            trim: true,
        },
        url: {
            type: String,
            required: [true, 'Please add the source URL'],
        },
        isEnabled: {
            type: Boolean,
            default: true,
        },
        scraperScript: {
            type: String,
            required: true,
        },
        schedule: {
            enabled: { type: Boolean, default: false },
            cronExpression: { type: String, default: '0 2 * * *' }, // Daily 2AM
            type: { type: String, enum: ['daily', 'weekly', 'custom'], default: 'daily' },
        },
        config: {
            maxPages: { type: Number, default: 3 },
            rateLimit: { type: Number, default: 2000 }, // ms between requests
            defaultLocation: { type: String },
        },
        health: {
            lastScrapeAt: { type: Date },
            lastSuccessAt: { type: Date },
            lastFailureAt: { type: Date },
            successRate: { type: Number, default: 100 },
            avgResponseTime: { type: Number, default: 0 },
            isBlocked: { type: Boolean, default: false },
            blockDetectedAt: { type: Date },
            totalScraped: { type: Number, default: 0 },
        },
        status: {
            type: String,
            enum: ['active', 'paused', 'disabled', 'blocked'],
            default: 'active',
        },
        addedBy: {
            type: mongoose.Schema.ObjectId,
            ref: 'User',
        },
    },
    {
        timestamps: true,
    }
);

module.exports = mongoose.model('ScrapingSource', scrapingSourceSchema);
