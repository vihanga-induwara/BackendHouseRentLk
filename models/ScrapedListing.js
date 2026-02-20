const mongoose = require('mongoose');

const scrapedListingSchema = mongoose.Schema(
    {
        // Source tracking
        source: {
            type: mongoose.Schema.ObjectId,
            ref: 'ScrapingSource',
            required: true,
        },
        sourceWebsite: {
            type: String,
            required: true,
        },
        sourceUrl: {
            type: String,
            required: true,
            unique: true,
        },
        sourceId: {
            type: String,
        },

        // Normalized property data
        title: {
            type: String,
            required: true,
            trim: true,
        },
        description: {
            type: String,
            default: '',
        },
        descriptionSnippet: {
            type: String,
            default: '',
        },
        price: {
            type: Number,
            default: 0,
        },
        location: {
            town: { type: String, default: '' },
            district: { type: String, default: '' },
            province: { type: String, default: '' },
            rawAddress: { type: String, default: '' },
        },
        beds: { type: Number, default: 0 },
        baths: { type: Number, default: 0 },
        size: { type: Number, default: 0 },
        type: {
            type: String,
            enum: ['House', 'Boarding Room', 'Annex', 'Apartment', 'Other', 'Unknown'],
            default: 'Unknown',
        },
        furnished: {
            type: String,
            enum: ['Furnished', 'Unfurnished', 'Semi-Furnished', 'Unknown'],
            default: 'Unknown',
        },
        images: {
            type: [String],
            default: [],
        },

        // Scraping metadata
        scrapedAt: {
            type: Date,
            default: Date.now,
        },
        lastChecked: {
            type: Date,
        },
        isActive: {
            type: Boolean,
            default: true,
        },
        expiresAt: {
            type: Date,
        },

        // PII Detection
        piiDetected: {
            type: Boolean,
            default: false,
        },
        piiDetails: {
            type: [String],
            default: [],
        },

        // AI Enrichment
        aiAnalysis: {
            estimatedFairPrice: { type: Number },
            priceRating: { type: String, enum: ['Below Market', 'Fair', 'Above Market', 'Unknown'], default: 'Unknown' },
            qualityScore: { type: Number, default: 0 },
            scamRiskScore: { type: Number, default: 0 },
            locationInsights: { type: String, default: '' },
            comparisonToLocal: { type: String, default: '' },
            tags: { type: [String], default: [] },
            marketTrend: { type: String, enum: ['Rising', 'Stable', 'Declining', 'Unknown'], default: 'Unknown' },
            dataCompleteness: { type: Number, default: 0 },
            analyzedAt: { type: Date },
        },

        // Approval workflow
        adminStatus: {
            type: String,
            enum: ['pending', 'approved', 'hidden', 'flagged', 'expired'],
            default: 'pending',
        },
        adminNotes: {
            type: String,
            default: '',
        },
        assignedTo: {
            type: mongoose.Schema.ObjectId,
            ref: 'User',
        },
        reviewedBy: {
            type: mongoose.Schema.ObjectId,
            ref: 'User',
        },
        reviewedAt: {
            type: Date,
        },

        // Display controls
        showFullDescription: {
            type: Boolean,
            default: false,
        },
        showImages: {
            type: Boolean,
            default: true,
        },

        // Tracking
        views: {
            type: Number,
            default: 0,
        },
        clickThroughs: {
            type: Number,
            default: 0,
        },
    },
    {
        timestamps: true,
    }
);

// Auto-generate snippet from description
scrapedListingSchema.pre('save', function (next) {
    if (this.description && !this.descriptionSnippet) {
        this.descriptionSnippet = this.description.substring(0, 200) + (this.description.length > 200 ? '...' : '');
    }
    // Set expiry to 30 days from scrape if not set
    if (!this.expiresAt) {
        const expiry = new Date(this.scrapedAt || Date.now());
        expiry.setDate(expiry.getDate() + 30);
        this.expiresAt = expiry;
    }
    next();
});

// Calculate data completeness
scrapedListingSchema.methods.calculateCompleteness = function () {
    const fields = ['title', 'description', 'price', 'location.town', 'beds', 'baths', 'size', 'type', 'furnished'];
    let filled = 0;
    fields.forEach(f => {
        const parts = f.split('.');
        let val = this;
        for (const p of parts) val = val?.[p];
        if (val && val !== 0 && val !== 'Unknown' && val !== '') filled++;
    });
    return Math.round((filled / fields.length) * 100);
};

// scrapedListingSchema.index({ sourceUrl: 1 }, { unique: true }); // Deduplicated by field definition
scrapedListingSchema.index({ adminStatus: 1 });
scrapedListingSchema.index({ 'location.town': 1 });
scrapedListingSchema.index({ sourceWebsite: 1 });
scrapedListingSchema.index({ scrapedAt: -1 });

module.exports = mongoose.model('ScrapedListing', scrapedListingSchema);
