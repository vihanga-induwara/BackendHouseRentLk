const express = require('express');
const router = express.Router();
const {
    getAdminListings,
    updateListingStatus,
} = require('../controllers/listingController');
const {
    getUsers,
    getUserDetails,
    updateUserStatus,
    updateUser,
    deleteUser,
    getStats
} = require('../controllers/adminController');
const {
    getPlatformHealth,
    getActivitySummary
} = require('../controllers/adminAnalyticsController');
const { protect, authorize } = require('../middleware/authMiddleware');

// All routes are protected and require admin role
router.use(protect);
router.use(authorize('admin'));

// Listing Management
router.get('/listings', getAdminListings);
router.put('/listings/:id/status', updateListingStatus);

// User Management
router.get('/users', getUsers);
router.route('/users/:id')
    .get(getUserDetails)
    .put(updateUser)
    .delete(deleteUser);
router.put('/users/:id/status', updateUserStatus);

// Dashboard Stats
router.get('/stats', getStats);
router.get('/health-analytics', getPlatformHealth);
router.get('/activity-summary', getActivitySummary);

module.exports = router;
