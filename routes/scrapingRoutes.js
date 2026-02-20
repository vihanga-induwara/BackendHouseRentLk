const express = require('express');
const router = express.Router();
const {
    // Sources
    getSources, addSource, updateSource, toggleSource, killSource, deleteSource,
    // Jobs
    triggerScrape, getJobs, getJobDetail, stopJob,
    // Listings
    getScrapedListings, getScrapedListing, editScrapedListing,
    approveScrapedListing, hideScrapedListing, flagScrapedListing,
    assignScrapedListing, reAnalyzeListing, bulkAction,
    // Health & Stats
    getHealth, getScrapingStats,
    // Market Intelligence
    getMarketReport, getPriceComparison, getHotAreas, getDataQuality,
    // Exposure & Conversion
    getExposureRules, getConversionStats,
    // Public
    getExternalListings, trackClickThrough,
} = require('../controllers/scrapingController');
const { protect, authorize } = require('../middleware/authMiddleware');

// ═══════════════════════════════════════
//   PUBLIC ROUTES (no auth required)
// ═══════════════════════════════════════
router.get('/external-listings', getExternalListings);
router.post('/external-listings/:id/click', trackClickThrough);

// ═══════════════════════════════════════
//   ADMIN ROUTES (auth + admin role)
// ═══════════════════════════════════════
router.use('/admin', protect, authorize('admin'));

// Source Management
router.route('/admin/sources')
    .get(getSources)
    .post(addSource);
router.route('/admin/sources/:id')
    .put(updateSource)
    .delete(deleteSource);
router.put('/admin/sources/:id/toggle', toggleSource);
router.post('/admin/sources/:id/kill', killSource);

// Scrape Job Operations
router.post('/admin/trigger', triggerScrape);
router.get('/admin/jobs', getJobs);
router.get('/admin/jobs/:id', getJobDetail);
router.post('/admin/jobs/:id/stop', stopJob);

// Scraped Listing Moderation
router.get('/admin/listings', getScrapedListings);
router.post('/admin/listings/bulk', bulkAction);
router.route('/admin/listings/:id')
    .get(getScrapedListing)
    .put(editScrapedListing);
router.put('/admin/listings/:id/approve', approveScrapedListing);
router.put('/admin/listings/:id/hide', hideScrapedListing);
router.put('/admin/listings/:id/flag', flagScrapedListing);
router.put('/admin/listings/:id/assign', assignScrapedListing);
router.post('/admin/listings/:id/analyze', reAnalyzeListing);

// Health & Stats
router.get('/admin/health', getHealth);
router.get('/admin/stats', getScrapingStats);

// Market Intelligence
router.get('/admin/market-report', getMarketReport);
router.get('/admin/price-comparison', getPriceComparison);
router.get('/admin/hot-areas', getHotAreas);
router.get('/admin/data-quality', getDataQuality);

// Exposure & Conversion
router.get('/admin/exposure-rules', getExposureRules);
router.get('/admin/conversion-stats', getConversionStats);

module.exports = router;
