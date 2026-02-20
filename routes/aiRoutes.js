const express = require('express');
const router = express.Router();
const {
    getSuggestedPrice,
    generateTitle,
    getListingInsights,
    autoTagListing,
    getReviewSentiment,
    getPriceFairness,
    // Phase 2
    nlpSearch,
    analyzeImageQuality,
    checkDuplicates,
    checkSpam,
    compareListings,
    getDemandHeatmap,
    getAreaSafety
} = require('../controllers/aiController');
const { protect } = require('../middleware/authMiddleware');

// ---- Phase 1 ----
// Public endpoints
router.get('/price-suggest', getSuggestedPrice);
router.get('/price-fairness/:listingId', getPriceFairness);
router.get('/sentiment/:listingId', getReviewSentiment);

// Private endpoints (require login)
router.post('/generate-title', protect, generateTitle);
router.post('/auto-tag', protect, autoTagListing);
router.get('/insights/:listingId', protect, getListingInsights);

// ---- Phase 2 ----
// Public endpoints
router.post('/nlp-search', nlpSearch);
router.post('/compare', compareListings);
router.get('/demand-heatmap', getDemandHeatmap);
router.get('/safety-score/:listingId', getAreaSafety);

// Private endpoints
router.post('/image-quality', protect, analyzeImageQuality);
router.post('/duplicate-check', protect, checkDuplicates);
router.post('/spam-check', protect, checkSpam);

module.exports = router;
