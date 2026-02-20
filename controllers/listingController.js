const asyncHandler = require('express-async-handler');
const fs = require('fs');
const csv = require('csv-parser');
const Listing = require('../models/Listing');
const Favorite = require('../models/Favorite');
const Inquiry = require('../models/Inquiry');
const Report = require('../models/Report');
const Booking = require('../models/Booking');
const Review = require('../models/Review');
const { createNotification } = require('./notificationController');
const aiService = require('../services/aiService');

// @desc    Get all listings (Public - Approved Only)
// @route   GET /api/listings
// @access  Public
const getListings = asyncHandler(async (req, res) => {
    const {
        town,
        minPrice,
        maxPrice,
        beds,
        type,
        furnished,
        sort,
        page = 1,
        limit = 12
    } = req.query;

    const query = {
        status: 'approved',
        $or: [
            { expiresAt: { $gt: new Date() } },
            { expiresAt: { $exists: false } },
            { expiresAt: null }
        ]
    };

    // Escape regex to prevent injection
    const escapeRegex = (text) => text.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&');

    // Advanced Filtering
    if (town) query['location.town'] = { $regex: escapeRegex(town), $options: 'i' };
    if (minPrice || maxPrice) {
        query.price = {};
        if (minPrice) query.price.$gte = Number(minPrice);
        if (maxPrice) query.price.$lte = Number(maxPrice);
    }
    if (beds) query.beds = beds === '4+' ? { $gte: 4 } : Number(beds);
    if (type && type !== 'Any') query.type = type;
    if (furnished && furnished !== 'Any') query.furnished = furnished;

    // Amenities
    const amenities = ['solarPower', 'ac', 'parking', 'wifi', 'garden'];
    amenities.forEach(amenity => {
        if (req.query[amenity] === 'true') {
            query[`amenities.${amenity}`] = true;
        }
    });

    // Pagination & Sorting
    const skip = (Number(page) - 1) * Number(limit);
    let sortQuery = { createdAt: -1 }; // Default: Newest

    if (sort === 'price_asc') sortQuery = { price: 1 };
    if (sort === 'price_desc') sortQuery = { price: -1 };
    if (sort === 'views') sortQuery = { views: -1 };

    const listings = await Listing.find(query)
        .populate('owner', 'name email phone avatar')
        .sort(sortQuery)
        .skip(skip)
        .limit(Number(limit));

    const total = await Listing.countDocuments(query);

    res.status(200).json({
        success: true,
        count: listings.length,
        total,
        pages: Math.ceil(total / Number(limit)),
        data: listings
    });
});

// @desc    Get single listing
// @route   GET /api/listings/:id
// @access  Public
const getListing = asyncHandler(async (req, res) => {
    const listing = await Listing.findById(req.params.id).populate('owner', 'name email phone avatar');

    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    // Increment views
    listing.views = (listing.views || 0) + 1;
    await listing.save({ validateBeforeSave: false });

    res.status(200).json(listing);
});

// @desc    Get my listings
// @route   GET /api/listings/my-listings
// @access  Private
const getMyListings = asyncHandler(async (req, res) => {
    const listings = await Listing.find({ owner: req.user.id });
    res.status(200).json(listings);
});

// Helper to generate AI content
const generateAIContent = async (listingData) => {
    try {
        return await aiService.executeScript('ai_service.py', listingData);
    } catch (error) {
        console.error("AI Generation failed:", error.message);
        return null; // Graceful fallback
    }
};

// @desc    Create new listing
// @route   POST /api/listings
// @access  Private (Owner/Broker)
const createListing = asyncHandler(async (req, res) => {
    // Verification Check
    if (!req.user.isEmailVerified && !req.user.isPhoneVerified) {
        res.status(403);
        throw new Error('You must verify your Email or Phone Number before posting an ad.');
    }

    const listingData = { ...req.body, owner: req.user.id, status: 'pending' };

    // Auto-set expiry to 30 days from now
    listingData.expiresAt = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);

    // Generate AI Description
    const aiContent = await generateAIContent(listingData);
    if (aiContent) {
        listingData.aiDescription = {
            description: aiContent.description,
            townVibe: aiContent.townVibe,
            generatedAt: new Date()
        };
    }

    // Auto-tag listing using NLP
    try {
        const tagResult = await aiService.executeScript('auto_tagger.py', {
            title: listingData.title || '',
            description: listingData.description || '',
            amenities: listingData.amenities || {},
            furnished: listingData.furnished || 'Unfurnished'
        });

        if (tagResult && tagResult.tags) {
            listingData.autoTags = tagResult.tags;
            listingData.nearbyPlaces = tagResult.nearbyPlaces || [];
        }
    } catch (error) {
        console.error("Auto-tagging failed", error);
    }

    const listing = await Listing.create(listingData);
    res.status(201).json(listing);
});

// @desc    Update listing
// @route   PUT /api/listings/:id
// @access  Private (Owner/Admin)
const updateListing = asyncHandler(async (req, res) => {
    const listing = await Listing.findById(req.params.id);

    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    if (listing.owner.toString() !== req.user.id && req.user.role !== 'admin') {
        res.status(401);
        throw new Error('Not authorized');
    }

    // If owner updates, reset status to pending (unless admin)
    let updateData = req.body;
    if (req.user.role !== 'admin') {
        updateData.status = 'pending';
    }

    // Refresh AI Content if critical fields change
    if (updateData.description || updateData.location || updateData.amenities) {
        // Merge current listing data with update data for context
        const contextData = { ...listing.toObject(), ...updateData };
        const aiContent = await generateAIContent(contextData);
        if (aiContent) {
            updateData.aiDescription = {
                description: aiContent.description,
                townVibe: aiContent.townVibe,
                generatedAt: new Date()
            };
        }
    }

    const updatedListing = await Listing.findByIdAndUpdate(req.params.id, updateData, { new: true });
    res.status(200).json(updatedListing);
});

// @desc    Delete listing
// @route   DELETE /api/listings/:id
// @access  Private (Owner/Admin)
const deleteListing = asyncHandler(async (req, res) => {
    const listing = await Listing.findById(req.params.id);

    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    if (listing.owner.toString() !== req.user.id && req.user.role !== 'admin') {
        res.status(401);
        throw new Error('Not authorized');
    }

    // Cascading delete: Remove all associated data
    await Promise.all([
        Booking.deleteMany({ listing: listing._id }),
        Review.deleteMany({ listing: listing._id }),
        Inquiry.deleteMany({ listing: listing._id }),
        Favorite.deleteMany({ listingId: listing._id }),
        Report.deleteMany({ listing: listing._id })
    ]);

    await listing.deleteOne();
    res.status(200).json({ id: req.params.id });
});

// @desc    Get all listings (Admin)
// @route   GET /api/admin/listings
// @access  Private (Admin)
const getAdminListings = asyncHandler(async (req, res) => {
    const listings = await Listing.find().populate('owner', 'name email');
    res.status(200).json(listings);
});

// @desc    Update listing status (Admin)
// @route   PUT /api/admin/listings/:id/status
// @access  Private (Admin)
const updateListingStatus = asyncHandler(async (req, res) => {
    const { status } = req.body;

    const listing = await Listing.findById(req.params.id);

    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    listing.status = status;
    const updatedListing = await listing.save();

    // Notify the listing owner
    if (status === 'approved' || status === 'rejected') {
        await createNotification({
            userId: listing.owner,
            type: status === 'approved' ? 'listing_approved' : 'listing_rejected',
            title: status === 'approved' ? 'Listing Approved! 🎉' : 'Listing Rejected',
            message: status === 'approved'
                ? `Your listing "${listing.title}" has been approved and is now live!`
                : `Your listing "${listing.title}" was rejected. Please review and resubmit.`,
            link: '/my-listings',
        });
    }

    res.status(200).json(updatedListing);
});

// @desc    Toggle listing status (Owner: pause, rented, relist)
// @route   PUT /api/listings/:id/status
// @access  Private (Owner)
const toggleListingStatus = asyncHandler(async (req, res) => {
    const { status } = req.body;
    const allowedStatuses = ['paused', 'rented', 'pending']; // pending = relist

    if (!allowedStatuses.includes(status)) {
        res.status(400);
        throw new Error(`Invalid status. Allowed: ${allowedStatuses.join(', ')}`);
    }

    const listing = await Listing.findById(req.params.id);

    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    if (listing.owner.toString() !== req.user.id && req.user.role !== 'admin') {
        res.status(401);
        throw new Error('Not authorized');
    }

    listing.status = status;
    const updatedListing = await listing.save();
    res.status(200).json(updatedListing);
});

// @desc    Renew listing (reset expiry to 30 days)
// @route   PUT /api/listings/:id/renew
// @access  Private (Owner)
const renewListing = asyncHandler(async (req, res) => {
    const listing = await Listing.findById(req.params.id);

    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    if (listing.owner.toString() !== req.user.id) {
        res.status(401);
        throw new Error('Not authorized');
    }

    listing.expiresAt = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);
    listing.renewedAt = new Date();

    // If it was expired, set back to pending for re-approval
    if (listing.status === 'expired') {
        listing.status = 'pending';
    }

    const updatedListing = await listing.save();
    res.status(200).json(updatedListing);
});

// @desc    Get listing analytics
// @route   GET /api/listings/:id/analytics
// @access  Private (Owner/Admin)
const getListingAnalytics = asyncHandler(async (req, res) => {
    const listing = await Listing.findById(req.params.id);

    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    if (listing.owner.toString() !== req.user.id && req.user.role !== 'admin') {
        res.status(401);
        throw new Error('Not authorized');
    }

    const favoriteCount = await Favorite.countDocuments({ listingId: listing._id, removed: false });
    const inquiryCount = await Inquiry.countDocuments({ listing: listing._id });

    res.status(200).json({
        views: listing.views || 0,
        favorites: favoriteCount,
        inquiries: inquiryCount,
        shares: listing.shares || 0,
        createdAt: listing.createdAt,
    });
});

// @desc    Get market insights (price comparison)
// @route   GET /api/listings/:id/market-insights
// @access  Private (Owner/Admin)
const getMarketInsights = asyncHandler(async (req, res) => {
    const listing = await Listing.findById(req.params.id);

    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    // Get average price for similar properties in the same town
    const similarProperties = await Listing.aggregate([
        {
            $match: {
                status: 'approved',
                type: listing.type,
                'location.town': listing.location.town,
                _id: { $ne: listing._id }
            }
        },
        {
            $group: {
                _id: null,
                avgPrice: { $avg: '$price' },
                minPrice: { $min: '$price' },
                maxPrice: { $max: '$price' },
                count: { $sum: 1 }
            }
        }
    ]);

    const insight = similarProperties[0] || { avgPrice: 0, minPrice: 0, maxPrice: 0, count: 0 };

    const diff = insight.avgPrice ? Math.round(((listing.price - insight.avgPrice) / insight.avgPrice) * 100) : 0;

    res.status(200).json({
        yourPrice: listing.price,
        areaAverage: Math.round(insight.avgPrice),
        minPrice: insight.minPrice,
        maxPrice: insight.maxPrice,
        propertyCount: insight.count,
        difference: diff,
        percentDiff: Math.abs(diff),
        status: diff <= 0 ? 'good_deal' : 'above_average'
    });
});

// @desc    Duplicate listing
// @route   POST /api/listings/:id/duplicate
// @access  Private (Owner)
const duplicateListing = asyncHandler(async (req, res) => {
    const listing = await Listing.findById(req.params.id);

    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    if (listing.owner.toString() !== req.user.id) {
        res.status(401);
        throw new Error('Not authorized');
    }

    const listingObj = listing.toObject();

    // Remove system fields
    delete listingObj._id;
    delete listingObj.id;
    delete listingObj.createdAt;
    delete listingObj.updatedAt;
    delete listingObj.views;
    delete listingObj.renewedAt;
    delete listingObj.aiDescription;

    // Reset status and set new expiry
    listingObj.status = 'pending';
    listingObj.expiresAt = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);
    listingObj.title = `${listingObj.title} (Copy)`;

    const duplicated = await Listing.create(listingObj);
    res.status(201).json(duplicated);
});

// @desc    Bulk upload listings from CSV
// @route   POST /api/listings/bulk-upload
// @access  Private (Owner/Admin)
const bulkUploadListings = asyncHandler(async (req, res) => {
    if (!req.file) {
        res.status(400);
        throw new Error('Please upload a CSV file');
    }

    const listings = [];
    const results = {
        success: 0,
        errors: 0,
        failedRows: []
    };

    const cleanupFile = () => {
        if (req.file && fs.existsSync(req.file.path)) {
            try {
                fs.unlinkSync(req.file.path);
            } catch (cleanupErr) {
                console.error('Failed to delete uploaded file:', cleanupErr);
            }
        }
    };

    fs.createReadStream(req.file.path)
        .pipe(csv())
        .on('data', (row) => {
            try {
                // Basic mapping and validation
                if (!row.title || !row.price) return;

                listings.push({
                    title: row.title,
                    type: row.type || 'House',
                    price: Number(row.price),
                    description: row.description || '',
                    beds: Number(row.beds) || 1,
                    baths: Number(row.baths) || 1,
                    size: row.size || '1000 sqft',
                    location: {
                        town: row.town || 'Unknown',
                        address: row.address || ''
                    },
                    owner: req.user.id,
                    status: 'pending',
                    amenities: {
                        parking: row.parking === 'true',
                        wifi: row.wifi === 'true',
                        furnished: row.furnished === 'true'
                    }
                });
            } catch (err) {
                results.errors++;
            }
        })
        .on('error', (error) => {
            cleanupFile();
            res.status(500);
            throw new Error('CSV parsing failed: ' + error.message);
        })
        .on('end', async () => {
            try {
                if (listings.length > 0) {
                    const created = await Listing.insertMany(listings);
                    results.success = created.length;
                }
                res.status(201).json(results);
            } catch (err) {
                res.status(500);
                throw new Error('Batch insert failed: ' + err.message);
            } finally {
                cleanupFile();
            }
        });
});

// @desc    Get similar listings
// @route   GET /api/listings/:id/similar
// @access  Public
const getSimilarListings = asyncHandler(async (req, res) => {
    const listing = await Listing.findById(req.params.id);

    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    const similar = await Listing.find({
        _id: { $ne: listing._id },
        'location.town': listing.location.town,
        type: listing.type,
        status: 'approved'
    }).limit(4);

    res.status(200).json(similar);
});

// @desc    Report a listing
// @route   POST /api/listings/report
// @access  Private
const reportListing = asyncHandler(async (req, res) => {
    const { listingId, reason } = req.body;

    if (!listingId || !reason) {
        res.status(400);
        throw new Error('Listing ID and reason are required');
    }

    const listing = await Listing.findById(listingId);
    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    // Check for duplicate report
    const existing = await Report.findOne({ reporter: req.user.id, listing: listingId });
    if (existing) {
        res.status(400);
        throw new Error('You have already reported this listing');
    }

    const report = await Report.create({
        reporter: req.user.id,
        listing: listingId,
        reason
    });

    // Notify admins
    try {
        await createNotification({
            userId: listing.owner,
            type: 'listing_reported',
            title: 'Listing Reported',
            message: `Your listing "${listing.title}" has been reported and is under review.`,
            link: '/my-listings',
        });
    } catch (err) {
        console.error('Failed to send report notification:', err);
    }

    res.status(201).json({ message: 'Report submitted successfully', report });
});

module.exports = {
    getListings,
    getListing,
    getMyListings,
    createListing,
    updateListing,
    deleteListing,
    getAdminListings,
    updateListingStatus,
    toggleListingStatus,
    renewListing,
    getListingAnalytics,
    duplicateListing,
    getMarketInsights,
    bulkUploadListings,
    getSimilarListings,
    reportListing
};
