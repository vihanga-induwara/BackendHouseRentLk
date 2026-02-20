const express = require('express');
const router = express.Router();
const {
    updateRenterProfile,
    getMatchedListings,
    getMatchedRenters
} = require('../controllers/matchingController');
const { protect } = require('../middleware/authMiddleware');

router.put('/profile', protect, updateRenterProfile);
router.get('/listings', protect, getMatchedListings);
router.get('/renters/:listingId', protect, getMatchedRenters);

module.exports = router;
