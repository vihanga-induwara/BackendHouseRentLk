const mongoose = require('mongoose');

const scrapeJobSchema = mongoose.Schema(
    {
        triggeredBy: {
            type: mongoose.Schema.ObjectId,
            ref: 'User',
            required: true,
        },
        source: {
            type: mongoose.Schema.ObjectId,
            ref: 'ScrapingSource',
        },
        sources: [{
            type: String,
        }],
        type: {
            type: String,
            enum: ['full', 'incremental', 'recheck'],
            default: 'incremental',
        },
        status: {
            type: String,
            enum: ['running', 'completed', 'failed', 'partial', 'stopped'],
            default: 'running',
        },
        stoppedBy: {
            type: mongoose.Schema.ObjectId,
            ref: 'User',
        },
        startedAt: {
            type: Date,
            default: Date.now,
        },
        completedAt: {
            type: Date,
        },
        stats: {
            totalScraped: { type: Number, default: 0 },
            newListings: { type: Number, default: 0 },
            updated: { type: Number, default: 0 },
            duplicatesSkipped: { type: Number, default: 0 },
            inactiveDetected: { type: Number, default: 0 },
            piiAutoFlagged: { type: Number, default: 0 },
        },
        errorDetails: [{
            page: { type: Number },
            source: { type: String },
            message: { type: String },
            rawHtml: { type: String },
        }],
        parseErrors: [{
            field: { type: String },
            listingUrl: { type: String },
            message: { type: String },
        }],
        locationFilter: { type: String },
        priceRangeFilter: {
            min: { type: Number },
            max: { type: Number },
        },
        maxPages: { type: Number, default: 3 },
    },
    {
        timestamps: true,
    }
);

scrapeJobSchema.index({ status: 1 });
scrapeJobSchema.index({ startedAt: -1 });

module.exports = mongoose.model('ScrapeJob', scrapeJobSchema);
