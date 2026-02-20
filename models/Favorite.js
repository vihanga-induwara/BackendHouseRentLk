const mongoose = require('mongoose');

const favoriteSchema = mongoose.Schema(
    {
        userId: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'User',
            required: true
        },
        listingId: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'Listing',
            required: true
        },
        savedAt: {
            type: Date,
            default: Date.now
        },
        removed: {
            type: Boolean,
            default: false
        },
        removedAt: {
            type: Date
        }
    },
    {
        timestamps: true
    }
);

// Compound index to prevent duplicate favorites
favoriteSchema.index({ userId: 1, listingId: 1 }, { unique: true });

module.exports = mongoose.model('Favorite', favoriteSchema);
