const asyncHandler = require('express-async-handler');
const User = require('../models/User');
const { createNotification } = require('./notificationController');

// @desc    Submit verification documents
// @route   POST /api/verification/submit
// @access  Private
const submitVerification = asyncHandler(async (req, res) => {
    const { docs } = req.body; // Array of { type, url }

    if (!docs || !Array.isArray(docs) || docs.length === 0) {
        res.status(400);
        throw new Error('Please upload at least one verification document');
    }

    const user = await User.findById(req.user.id);

    user.verificationStatus = 'pending';
    user.verificationDocs = docs.map(doc => ({
        type: doc.type,
        url: doc.url,
        status: 'pending'
    }));
    user.verificationMessage = 'Under review by admin';

    await user.save();
    res.status(200).json({
        status: user.verificationStatus,
        docs: user.verificationDocs,
        message: user.verificationMessage
    });
});

// @desc    Get user verification status
// @route   GET /api/verification/status
// @access  Private
const getVerificationStatus = asyncHandler(async (req, res) => {
    const user = await User.findById(req.user.id);
    res.status(200).json({
        status: user.verificationStatus,
        docs: user.verificationDocs,
        message: user.verificationMessage,
        verifiedAt: user.verifiedAt
    });
});

// @desc    Get all pending verifications (Admin)
// @route   GET /api/verification/admin/pending
// @access  Private/Admin
const getPendingVerifications = asyncHandler(async (req, res) => {
    const users = await User.find({ verificationStatus: 'pending' })
        .select('name email phone verificationStatus verificationDocs');
    res.status(200).json(users);
});

// @desc    Review verification request (Admin)
// @route   PUT /api/verification/admin/:userId
// @access  Private/Admin
const reviewVerification = asyncHandler(async (req, res) => {
    const { status, message } = req.body; // verified, rejected

    if (!['verified', 'rejected'].includes(status)) {
        res.status(400);
        throw new Error('Invalid status. Use "verified" or "rejected".');
    }

    const user = await User.findById(req.params.userId);

    if (!user) {
        res.status(404);
        throw new Error('User not found');
    }

    user.verificationStatus = status;
    user.verificationMessage = message || (status === 'verified' ? 'Identity verified successfully' : 'Verification rejected');

    if (status === 'verified') {
        user.verifiedAt = Date.now();
        user.isVerified = true;
        // Also approve all pending docs
        user.verificationDocs.forEach(doc => {
            if (doc.status === 'pending') doc.status = 'approved';
        });
    } else {
        user.isVerified = false;
        // Optionally mark docs as rejected
        user.verificationDocs.forEach(doc => {
            if (doc.status === 'pending') doc.status = 'rejected';
        });
    }

    await user.save();

    // Notify user
    await createNotification({
        userId: user._id,
        type: status === 'verified' ? 'verification_approved' : 'verification_rejected',
        title: status === 'verified' ? 'Identity Verified! ✅' : 'Verification Update',
        message: user.verificationMessage,
        link: '/profile',
    });

    res.status(200).json({
        status: user.verificationStatus,
        message: user.verificationMessage
    });
});

module.exports = {
    submitVerification,
    getVerificationStatus,
    getPendingVerifications,
    reviewVerification,
};
