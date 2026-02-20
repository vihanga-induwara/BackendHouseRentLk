const mongoose = require('mongoose');

const reviewSchema = new mongoose.Schema(
    {
        listing: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'Listing',
            required: true,
        },
        reviewer: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'User',
            required: true,
        },
        rating: {
            type: Number,
            required: [true, 'Please add a rating between 1 and 5'],
            min: 1,
            max: 5,
        },
        comment: {
            type: String,
            required: [true, 'Please add a comment'],
            maxlength: 500,
        },
    },
    { timestamps: true }
);

// Prevent user from submitting more than one review per listing
reviewSchema.index({ listing: 1, reviewer: 1 }, { unique: true });

module.exports = mongoose.model('Review', reviewSchema);
