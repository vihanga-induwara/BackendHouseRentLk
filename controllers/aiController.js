const asyncHandler = require('express-async-handler');
const Listing = require('../models/Listing');
const Favorite = require('../models/Favorite');
const Inquiry = require('../models/Inquiry');
const Review = require('../models/Review');
const SavedSearch = require('../models/SavedSearch');
const aiService = require('../services/aiService');

// @desc    Get AI-suggested price for a listing
// @route   GET /api/ai/price-suggest
// @access  Public
const getSuggestedPrice = asyncHandler(async (req, res) => {
    let { town, beds, baths, size } = req.query;

    if (!town || !beds) {
        res.status(400);
        throw new Error('Town and beds are required');
    }

    // Basic sanitization
    const sanitize = (str) => String(str).replace(/[;&|`$]/g, '').trim().substring(0, 100);
    town = sanitize(town);

    const result = await aiService.executeScript('pricing_engine.py', {
        town,
        beds: Number(beds),
        baths: Number(baths || 1),
        size: Number(size || 1000)
    });

    res.status(200).json(result);
});

// @desc    Generate smart title for a listing
// @route   POST /api/ai/generate-title
// @access  Private
const generateTitle = asyncHandler(async (req, res) => {
    const { type, beds, baths, town, price, tenantType, amenities, furnished } = req.body;

    if (!town || !beds || !type) {
        res.status(400);
        throw new Error('Town, beds, and type are required');
    }

    const result = await aiService.executeScript('title_generator.py', {
        type,
        beds: Number(beds),
        baths: Number(baths || 1),
        town,
        price: Number(price || 0),
        tenantType: tenantType || 'Any',
        amenities: amenities || {},
        furnished: furnished || 'Unfurnished'
    });

    res.status(200).json(result);
});

// @desc    Get AI performance insights for a listing
// @route   GET /api/ai/insights/:listingId
// @access  Private (Owner)
const getListingInsights = asyncHandler(async (req, res) => {
    const listing = await Listing.findById(req.params.listingId);

    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    // Only listing owner or admin can see insights
    if (listing.owner.toString() !== req.user.id && req.user.role !== 'admin') {
        res.status(403);
        throw new Error('Not authorized');
    }

    // Get counts for this listing
    const favoriteCount = await Favorite.countDocuments({ listingId: listing._id, removed: false });
    const inquiryCount = await Inquiry.countDocuments({ listing: listing._id });

    // Get peer statistics (same town + type)
    const peers = await Listing.find({
        'location.town': listing.location.town,
        type: listing.type,
        _id: { $ne: listing._id },
        status: 'approved'
    });

    const peerStats = {
        count: peers.length,
        avgViews: peers.length > 0 ? peers.reduce((sum, p) => sum + (p.views || 0), 0) / peers.length : 50,
        avgImages: peers.length > 0 ? peers.reduce((sum, p) => sum + (p.images?.length || 0), 0) / peers.length : 4,
        avgPrice: peers.length > 0 ? peers.reduce((sum, p) => sum + (p.price || 0), 0) / peers.length : 40000
    };

    const result = await aiService.executeScript('performance_analyzer.py', {
        listing: {
            views: listing.views || 0,
            shares: listing.shares || 0,
            images: listing.images || [],
            price: listing.price,
            title: listing.title,
            description: listing.description,
            video: listing.video,
            furnished: listing.furnished,
            inquiryCount,
            favoriteCount
        },
        peerStats
    });

    res.status(200).json(result);
});

// @desc    Extract auto-tags from listing data
// @route   POST /api/ai/auto-tag
// @access  Private
const autoTagListing = asyncHandler(async (req, res) => {
    const { title, description, amenities, furnished } = req.body;

    const result = await aiService.executeScript('auto_tagger.py', {
        title: title || '',
        description: description || '',
        amenities: amenities || {},
        furnished: furnished || 'Unfurnished'
    });

    res.status(200).json(result);
});

// @desc    Get review sentiment analysis for a listing
// @route   GET /api/ai/sentiment/:listingId
// @access  Public
const getReviewSentiment = asyncHandler(async (req, res) => {
    const reviews = await Review.find({ listing: req.params.listingId })
        .select('comment _id rating');

    if (!reviews || reviews.length === 0) {
        return res.status(200).json({
            overallScore: 50,
            overallLabel: 'neutral',
            totalPositive: 0,
            totalNegative: 0,
            totalNeutral: 0,
            reviewSentiments: []
        });
    }

    const result = await aiService.executeScript('sentiment_analyzer.py', {
        reviews: reviews.map(r => ({
            _id: r._id.toString(),
            comment: r.comment,
            rating: r.rating
        }))
    });

    res.status(200).json(result);
});

// @desc    Get price fairness score for a listing
// @route   GET /api/ai/price-fairness/:listingId
// @access  Public
const getPriceFairness = asyncHandler(async (req, res) => {
    const listing = await Listing.findById(req.params.listingId);

    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    // Get similar listings in the same town
    const similar = await Listing.find({
        'location.town': listing.location.town,
        type: listing.type,
        status: 'approved',
        _id: { $ne: listing._id }
    }).select('price');

    if (similar.length === 0) {
        return res.status(200).json({
            score: 'unknown',
            marketAvg: null,
            percentDiff: 0,
            message: 'Not enough data in this area to compare',
            sampleSize: 0
        });
    }

    const avgPrice = similar.reduce((sum, s) => sum + s.price, 0) / similar.length;
    const percentDiff = ((listing.price - avgPrice) / avgPrice) * 100;

    let score, message;
    if (percentDiff <= -15) {
        score = 'great_deal';
        message = `${Math.abs(Math.round(percentDiff))}% below market average — Great Deal!`;
    } else if (percentDiff <= 10) {
        score = 'fair';
        message = 'Price matches market average — Fair Price';
    } else {
        score = 'above_market';
        message = `${Math.round(percentDiff)}% above market average`;
    }

    res.status(200).json({
        score,
        marketAvg: Math.round(avgPrice),
        listingPrice: listing.price,
        percentDiff: Math.round(percentDiff),
        message,
        sampleSize: similar.length
    });
});

// ========================
// PHASE 2 ENDPOINTS
// ========================

// @desc    Parse NLP search query into structured filters
// @route   POST /api/ai/nlp-search
// @access  Public
const nlpSearch = asyncHandler(async (req, res) => {
    const { query } = req.body;

    if (!query || query.trim().length < 3) {
        res.status(400);
        throw new Error('Search query is required (min 3 characters)');
    }

    const result = await aiService.executeScript('nlp_search.py', { query: query.trim() });
    res.status(200).json(result);
});

// @desc    Analyze image quality for a listing upload
// @route   POST /api/ai/image-quality
// @access  Private
const analyzeImageQuality = asyncHandler(async (req, res) => {
    const { images } = req.body;
    // images: array of { width, height, sizeKb }
    const result = await aiService.executeScript('image_quality.py', { images: images || [] });
    res.status(200).json(result);
});

// @desc    Detect duplicate listings by same owner
// @route   POST /api/ai/duplicate-check
// @access  Private
const checkDuplicates = asyncHandler(async (req, res) => {
    const { title, description, town, price, beds, baths, type } = req.body;

    // Find existing listings by same owner
    const existing = await Listing.find({
        owner: req.user.id,
        status: { $in: ['approved', 'pending'] }
    }).select('title description location price beds baths type').lean();

    const existingMapped = existing.map(l => ({
        _id: l._id.toString(),
        title: l.title || '',
        description: l.description || '',
        town: l.location?.town || '',
        price: l.price || 0,
        beds: l.beds || 0,
        baths: l.baths || 0,
        type: l.type || ''
    }));

    const result = await aiService.executeScript('duplicate_detector.py', {
        newListing: { title, description, town, price, beds, baths, type },
        existingListings: existingMapped
    });

    res.status(200).json(result);
});

// @desc    Check listing for spam/scam indicators
// @route   POST /api/ai/spam-check
// @access  Private
const checkSpam = asyncHandler(async (req, res) => {
    const { title, description, price, town } = req.body;
    const result = await aiService.executeScript('spam_detector.py', {
        title: title || '',
        description: description || '',
        price: Number(price) || 0,
        town: town || ''
    });
    res.status(200).json(result);
});

// @desc    Generate AI comparison summary for multiple listings
// @route   POST /api/ai/compare
// @access  Public
const compareListings = asyncHandler(async (req, res) => {
    const { listingIds } = req.body;

    if (!listingIds || listingIds.length < 2) {
        res.status(400);
        throw new Error('At least 2 listing IDs required');
    }

    const listings = await Listing.find({ _id: { $in: listingIds } })
        .select('title price beds baths size type furnished amenities location')
        .lean();

    const mapped = listings.map(l => ({
        title: l.title || '',
        price: l.price || 0,
        beds: l.beds || 0,
        baths: l.baths || 0,
        size: l.size || 0,
        type: l.type || '',
        furnished: l.furnished || 'Unfurnished',
        amenities: l.amenities || {},
        town: l.location?.town || ''
    }));

    const result = await aiService.executeScript('comparison_ai.py', { listings: mapped });
    res.status(200).json(result);
});

// @desc    Get real demand heatmap data by town
// @route   GET /api/ai/demand-heatmap
// @access  Public
const getDemandHeatmap = asyncHandler(async (req, res) => {
    // Aggregate listing data by town
    const townStats = await Listing.aggregate([
        { $match: { status: 'approved' } },
        {
            $group: {
                _id: '$location.town',
                listings: { $sum: 1 },
                totalViews: { $sum: { $ifNull: ['$views', 0] } },
                avgPrice: { $avg: '$price' }
            }
        },
        { $match: { _id: { $ne: null } } },
        { $sort: { listings: -1 } },
        { $limit: 30 }
    ]);

    // Get inquiry counts per town
    const inquiryStats = await Inquiry.aggregate([
        {
            $lookup: {
                from: 'listings',
                localField: 'listing',
                foreignField: '_id',
                as: 'listingData'
            }
        },
        { $unwind: '$listingData' },
        {
            $group: {
                _id: '$listingData.location.town',
                inquiryCount: { $sum: 1 }
            }
        }
    ]);

    const inquiryMap = {};
    inquiryStats.forEach(s => { inquiryMap[s._id] = s.inquiryCount; });

    // Get search counts per town (from saved searches)
    let searchMap = {};
    try {
        const searchStats = await SavedSearch.aggregate([
            { $group: { _id: '$filters.town', searchCount: { $sum: 1 } } }
        ]);
        searchStats.forEach(s => { searchMap[s._id] = s.searchCount; });
    } catch (e) {
        // SavedSearch model may not track this — graceful fallback
    }

    const towns = townStats.map(t => ({
        name: t._id,
        listings: t.listings,
        totalViews: t.totalViews,
        avgPrice: t.avgPrice,
        inquiryCount: inquiryMap[t._id] || 0,
        searchCount: searchMap[t._id] || 0
    }));

    const result = await aiService.executeScript('demand_analyzer.py', { towns });
    res.status(200).json(result);
});

// @desc    Get area safety score for a listing's neighborhood
// @route   GET /api/ai/safety-score/:listingId
// @access  Public
const getAreaSafety = asyncHandler(async (req, res) => {
    const listing = await Listing.findById(req.params.listingId);
    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    const reviews = await Review.find({ listing: listing._id })
        .select('comment rating').lean();

    const result = await aiService.executeScript('safety_scorer.py', {
        town: listing.location?.town || '',
        reviewData: {
            reviews: reviews.map(r => ({
                comment: r.comment || '',
                rating: r.rating || 3
            }))
        }
    });

    res.status(200).json(result);
});

module.exports = {
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
};
