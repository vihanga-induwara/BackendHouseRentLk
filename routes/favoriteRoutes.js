const express = require('express');
const router = express.Router();
const {
    saveFavorite,
    removeFavorite,
    getFavorites
} = require('../controllers/trackingController');
const { protect } = require('../middleware/authMiddleware');

// All favorites routes require authentication
router.use(protect);

router.post('/', saveFavorite);
router.get('/', getFavorites);
router.delete('/:listingId', removeFavorite);

module.exports = router;
