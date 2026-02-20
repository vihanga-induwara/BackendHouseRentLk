const express = require('express');
const router = express.Router();
const { addReview, getListingReviews, deleteReview } = require('../controllers/reviewController');
const { protect } = require('../middleware/authMiddleware');

router.route('/')
    .post(protect, addReview);

router.get('/:listingId', getListingReviews);

router.delete('/:id', protect, deleteReview);

module.exports = router;
