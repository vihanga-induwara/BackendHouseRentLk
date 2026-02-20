const express = require('express');
const router = express.Router();
const {
    submitVerification,
    getVerificationStatus,
    getPendingVerifications,
    reviewVerification,
} = require('../controllers/verificationController');
const { protect, authorize } = require('../middleware/authMiddleware');

router.route('/')
    .get(protect, getVerificationStatus)
    .post(protect, submitVerification);

router.get('/pending', protect, authorize('admin'), getPendingVerifications);
router.put('/:userId', protect, authorize('admin'), reviewVerification);

module.exports = router;
