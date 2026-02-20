const asyncHandler = require('express-async-handler');
const Review = require('../models/Review');
const Listing = require('../models/Listing');
const { createNotification } = require('./notificationController');

// @desc    Add a review
// @route   POST /api/reviews
// @access  Private
const addReview = asyncHandler(async (req, res) => {
    const { listingId, rating, comment } = req.body;

    const listing = await Listing.findById(listingId);
    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    // Check if user already reviewed
    const alreadyReviewed = await Review.findOne({ listing: listingId, reviewer: req.user._id });
    if (alreadyReviewed) {
        res.status(400);
        throw new Error('Listing already reviewed');
    }

    const review = await Review.create({
        listing: listingId,
        reviewer: req.user._id,
        rating: Number(rating),
        comment,
    });

    // Notify the owner
    try {
        await createNotification({
            userId: listing.owner,
            type: 'listing_reviewed',
            title: 'New Review on your listing! ⭐',
            message: `${req.user.name} left a ${rating}-star review on "${listing.title}"`,
            link: `/listings/${listingId}`,
        });
    } catch (e) { /* ignore notification errors */ }

    res.status(201).json(review);
});

// @desc    Get reviews for a listing
// @route   GET /api/reviews/:listingId
// @access  Public
const getListingReviews = asyncHandler(async (req, res) => {
    const reviews = await Review.find({ listing: req.params.listingId })
        .populate('reviewer', 'name avatar')
        .sort({ createdAt: -1 });

    res.status(200).json(reviews);
});

// @desc    Delete a review
// @route   DELETE /api/reviews/:id
// @access  Private (Owner of review or Admin)
const deleteReview = asyncHandler(async (req, res) => {
    const review = await Review.findById(req.params.id);

    if (!review) {
        res.status(404);
        throw new Error('Review not found');
    }

    if (review.reviewer.toString() !== req.user.id && req.user.role !== 'admin') {
        res.status(401);
        throw new Error('Not authorized');
    }

    await review.deleteOne();
    res.status(200).json({ message: 'Review removed' });
});

module.exports = {
    addReview,
    getListingReviews,
    deleteReview,
};
