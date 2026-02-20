const mongoose = require('mongoose');

const searchHistorySchema = mongoose.Schema(
    {
        userId: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'User',
            required: true
        },
        keyword: {
            type: String,
            default: ''
        },
        filters: {
            location: String,
            minPrice: Number,
            maxPrice: Number,
            propertyType: String,
            bedrooms: Number,
            furnished: String,
            petFriendly: Boolean
        },
        resultsCount: {
            type: Number,
            default: 0
        },
        searchedAt: {
            type: Date,
            default: Date.now
        }
    },
    {
        timestamps: true
    }
);

// Index for faster queries
searchHistorySchema.index({ userId: 1, searchedAt: -1 });

module.exports = mongoose.model('SearchHistory', searchHistorySchema);
