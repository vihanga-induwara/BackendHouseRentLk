const asyncHandler = require('express-async-handler');
const User = require('../models/User');
const Listing = require('../models/Listing');

// @desc    Update renter profile
// @route   PUT /api/matching/profile
// @access  Private
const updateRenterProfile = asyncHandler(async (req, res) => {
    const user = await User.findById(req.user.id);

    if (!user) {
        res.status(404);
        throw new Error('User not found');
    }

    user.renterProfile = {
        ...user.renterProfile,
        ...req.body,
        isActive: req.body.isActive !== undefined ? req.body.isActive : true
    };

    await user.save();
    res.status(200).json(user.renterProfile);
});

// @desc    Get matched listings for the current user
// @route   GET /api/matching/listings
// @access  Private
const getMatchedListings = asyncHandler(async (req, res) => {
    const user = await User.findById(req.user.id);

    if (!user || !user.renterProfile || !user.renterProfile.isActive) {
        return res.status(200).json([]);
    }

    const { preferredTowns, budgetMin, budgetMax, preferredType, bedsMin } = user.renterProfile;

    const query = {
        status: 'approved'
    };

    if (preferredTowns && preferredTowns.length > 0) {
        query['location.town'] = { $in: preferredTowns };
    }

    if (budgetMin !== undefined || budgetMax !== undefined) {
        query.price = {};
        if (budgetMin !== undefined) query.price.$gte = budgetMin;
        if (budgetMax !== undefined) query.price.$lte = budgetMax;
    }

    if (preferredType && preferredType.length > 0) {
        query.type = { $in: preferredType };
    }

    if (bedsMin !== undefined) {
        query.beds = { $gte: bedsMin };
    }

    const matchedListings = await Listing.find(query).sort('-createdAt').limit(20);
    res.status(200).json(matchedListings);
});

// @desc    Get matched renters for a listing (for Owners)
// @route   GET /api/matching/renters/:listingId
// @access  Private
const getMatchedRenters = asyncHandler(async (req, res) => {
    const listing = await Listing.findById(req.params.listingId);

    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    // Only owner or admin can see matching renters
    if (listing.owner.toString() !== req.user.id && req.user.role !== 'admin') {
        res.status(401);
        throw new Error('Not authorized');
    }

    const query = {
        'renterProfile.isActive': true,
        $or: [
            { 'renterProfile.preferredTowns': listing.location.town },
            { 'renterProfile.preferredTowns': { $size: 0 } },
            { 'renterProfile.preferredTowns': { $exists: false } }
        ]
    };

    // Filter by budget if profile specifies it
    // This is tricky because we want renters who CAN afford it
    // renterProfile.budgetMax >= listing.price
    query['renterProfile.budgetMax'] = { $gte: listing.price };

    // And listing has enough beds
    query['renterProfile.bedsMin'] = { $lte: listing.beds };

    const matchedRenters = await User.find(query)
        .select('name email phone renterProfile avatar verificationStatus isVerified')
        .limit(20);

    res.status(200).json(matchedRenters);
});

module.exports = {
    updateRenterProfile,
    getMatchedListings,
    getMatchedRenters
};
