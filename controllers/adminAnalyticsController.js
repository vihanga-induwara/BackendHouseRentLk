const asyncHandler = require('express-async-handler');
const Listing = require('../models/Listing');
const aiService = require('../services/aiService');

// @desc    Get platform health and heatmaps
// @route   GET /api/admin/health-analytics
// @access  Private (Admin)
const getPlatformHealth = asyncHandler(async (req, res) => {
    // Fetch all listings for comprehensive analysis
    const listings = await Listing.find({}, 'location.town status createdAt');

    try {
        const analytics = await aiService.executeScript('health_analytics.py', { listings });
        res.json(analytics);
    } catch (error) {
        res.status(500);
        throw new Error('Analytics engine failed: ' + error.message);
    }
});

// @desc    Get activity summary
// @route   GET /api/admin/activity-summary
// @access  Private (Admin)
const getActivitySummary = asyncHandler(async (req, res) => {
    const totalListings = await Listing.countDocuments();
    const pendingListings = await Listing.countDocuments({ status: 'pending' });
    const approvedListings = await Listing.countDocuments({ status: 'approved' });

    res.json({
        total: totalListings,
        pending: pendingListings,
        activeRate: totalListings > 0 ? ((approvedListings / totalListings) * 100).toFixed(1) + '%' : '0%'
    });
});

module.exports = {
    getPlatformHealth,
    getActivitySummary
};
