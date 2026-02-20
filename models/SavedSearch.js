const mongoose = require('mongoose');

const savedSearchSchema = mongoose.Schema(
    {
        user: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'User',
            required: true
        },
        name: {
            type: String,
            required: [true, 'Please add a name for this alert'],
            trim: true
        },
        filters: {
            town: String,
            minPrice: Number,
            maxPrice: Number,
            type: String,
            beds: String,
            amenities: {
                ac: Boolean,
                parking: Boolean,
                wifi: Boolean
            }
        },
        isAlertActive: {
            type: Boolean,
            default: true
        },
        lastNotifiedAt: {
            type: Date,
            default: Date.now
        }
    },
    {
        timestamps: true
    }
);

module.exports = mongoose.model('SavedSearch', savedSearchSchema);
