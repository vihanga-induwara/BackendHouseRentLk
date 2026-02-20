const mongoose = require('mongoose');

const userActivitySchema = mongoose.Schema(
    {
        userId: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'User'
        },
        listingId: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'Listing',
            required: true
        },
        action: {
            type: String,
            enum: ['view', 'contact_click', 'share', 'phone_reveal', 'image_click', 'section_expand'],
            required: true
        },
        duration: {
            type: Number, // seconds spent on page
            default: 0
        },
        scrollDepth: {
            type: Number, // percentage scrolled (0-100)
            min: 0,
            max: 100,
            default: 0
        },
        contactMethod: {
            type: String,
            enum: ['phone', 'whatsapp', 'chat', 'email'],
        },
        imageIndex: {
            type: Number, // which image was clicked (0-based)
        },
        sectionName: {
            type: String, // e.g., 'amenities', 'location', 'description'
        },
        viewedAt: {
            type: Date,
            default: Date.now
        }
    },
    {
        timestamps: true
    }
);

// Indexes for analytics
userActivitySchema.index({ userId: 1, viewedAt: -1 });
userActivitySchema.index({ listingId: 1, viewedAt: -1 });
userActivitySchema.index({ action: 1, viewedAt: -1 });

module.exports = mongoose.model('UserActivity', userActivitySchema);
