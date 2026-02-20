const mongoose = require('mongoose');

const userAIProfileSchema = mongoose.Schema(
    {
        userId: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'User',
            required: true,
            unique: true
        },
        predictedBudgetRange: {
            min: {
                type: Number,
                default: 0
            },
            max: {
                type: Number,
                default: 100000
            }
        },
        preferredLocationCluster: {
            type: [String],
            default: []
        },
        seriousnessScore: {
            type: Number,
            min: 0,
            max: 100,
            default: 50
        },
        renterType: {
            type: String,
            enum: ['student', 'family', 'professional', 'unknown'],
            default: 'unknown'
        },
        priceSensitivityScore: {
            type: Number,
            min: 0,
            max: 100,
            default: 50
        },
        contactPreference: {
            type: String,
            enum: ['phone', 'whatsapp', 'chat', 'unknown'],
            default: 'unknown'
        },
        lastCalculated: {
            type: Date,
            default: Date.now
        }
    },
    {
        timestamps: true
    }
);

// Index for quick lookups
userAIProfileSchema.index({ userId: 1 });

module.exports = mongoose.model('UserAIProfile', userAIProfileSchema);
