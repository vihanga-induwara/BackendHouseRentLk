const asyncHandler = require('express-async-handler');
const ScrapingSource = require('../models/ScrapingSource');
const ScrapedListing = require('../models/ScrapedListing');
const ScrapeJob = require('../models/ScrapeJob');
const Listing = require('../models/Listing');
const aiService = require('../services/aiService');
const path = require('path');

// ═══════════════════════════════════════════
//   HELPER: Run scraper script
// ═══════════════════════════════════════════

const runScraperScript = async (scriptName, inputData) => {
    // Scrapers are located in ../utils/scrapers relative to this controller?
    // This controller is in Backend/controllers/
    // Scrapers are in Backend/utils/scrapers/
    // So distinct path is ../utils/scrapers
    const scrapersPath = path.join(__dirname, '../utils/scrapers');
    return await aiService.executeScript(scriptName, inputData, scrapersPath);
};

// ═══════════════════════════════════════════
//   HELPER: SSRF Vulnerability Preventer
// ═══════════════════════════════════════════

const validateExternalUrl = (urlString) => {
    try {
        const parsedUrl = new URL(urlString);
        const prohibitedHostnames = [
            'localhost', '127.0.0.1', '169.254.169.254',
            '10.0.0.0', '172.16.0.0', '192.168.0.0'
        ];
        // Checking for common internal network prefixes (e.g. AWS Instance Metadata, Localhost proxies)
        if (prohibitedHostnames.some(host => parsedUrl.hostname.includes(host)) || parsedUrl.hostname.endsWith('.local') || parsedUrl.hostname.endsWith('.internal')) {
            return false;
        }
        return ['http:', 'https:'].includes(parsedUrl.protocol);
    } catch (e) {
        return false;
    }
};

// ═══════════════════════════════════════════
//   1. SOURCE MANAGEMENT
// ═══════════════════════════════════════════

// @desc    Get all scraping sources
// @route   GET /api/admin/scraping/sources
const getSources = asyncHandler(async (req, res) => {
    const sources = await ScrapingSource.find().sort({ createdAt: -1 });
    res.status(200).json(sources);
});

// @desc    Add new scraping source
// @route   POST /api/admin/scraping/sources
const addSource = asyncHandler(async (req, res) => {
    const { name, slug, url, scraperScript, schedule, config } = req.body;

    if (!name || !slug || !url || !scraperScript) {
        res.status(400);
        throw new Error('Name, slug, URL, and scraper script are required');
    }

    if (!validateExternalUrl(url)) {
        res.status(400);
        throw new Error(`The provided URL is invalid or blocked for security reasons (SSRF).`);
    }

    const existing = await ScrapingSource.findOne({ slug });
    if (existing) {
        res.status(400);
        throw new Error(`Source with slug "${slug}" already exists`);
    }

    const source = await ScrapingSource.create({
        name, slug, url, scraperScript,
        schedule: schedule || {},
        config: config || {},
        addedBy: req.user.id,
    });

    res.status(201).json(source);
});

// @desc    Update scraping source
// @route   PUT /api/admin/scraping/sources/:id
const updateSource = asyncHandler(async (req, res) => {
    const source = await ScrapingSource.findById(req.params.id);
    if (!source) {
        res.status(404);
        throw new Error('Source not found');
    }

    const { name, url, scraperScript, schedule, config, isEnabled } = req.body;

    if (url !== undefined && !validateExternalUrl(url)) {
        res.status(400);
        throw new Error(`The provided URL is invalid or blocked for security reasons (SSRF).`);
    }

    if (name !== undefined) source.name = name;
    if (url !== undefined) source.url = url;
    if (scraperScript !== undefined) source.scraperScript = scraperScript;
    if (schedule !== undefined) source.schedule = { ...source.schedule.toObject?.() || source.schedule, ...schedule };
    if (config !== undefined) source.config = { ...source.config.toObject?.() || source.config, ...config };
    if (isEnabled !== undefined) source.isEnabled = isEnabled;

    await source.save();
    res.status(200).json(source);
});

// @desc    Toggle source on/off
// @route   PUT /api/admin/scraping/sources/:id/toggle
const toggleSource = asyncHandler(async (req, res) => {
    const source = await ScrapingSource.findById(req.params.id);
    if (!source) {
        res.status(404);
        throw new Error('Source not found');
    }

    source.isEnabled = !source.isEnabled;
    source.status = source.isEnabled ? 'active' : 'paused';
    await source.save();

    res.status(200).json({ message: `Source ${source.isEnabled ? 'enabled' : 'disabled'}`, source });
});

// @desc    Kill switch — disable source + hide all its listings
// @route   POST /api/admin/scraping/sources/:id/kill
const killSource = asyncHandler(async (req, res) => {
    const source = await ScrapingSource.findById(req.params.id);
    if (!source) {
        res.status(404);
        throw new Error('Source not found');
    }

    source.isEnabled = false;
    source.status = 'disabled';
    await source.save();

    // Hide all listings from this source
    const result = await ScrapedListing.updateMany(
        { source: source._id },
        { $set: { adminStatus: 'hidden' } }
    );

    res.status(200).json({
        message: `Source "${source.name}" killed. ${result.modifiedCount} listings hidden.`,
        source,
        listingsHidden: result.modifiedCount,
    });
});

// @desc    Delete scraping source
// @route   DELETE /api/admin/scraping/sources/:id
const deleteSource = asyncHandler(async (req, res) => {
    const source = await ScrapingSource.findById(req.params.id);
    if (!source) {
        res.status(404);
        throw new Error('Source not found');
    }

    // Remove all scraped listings from this source
    await ScrapedListing.deleteMany({ source: source._id });
    await source.deleteOne();

    res.status(200).json({ message: `Source "${source.name}" and all its listings deleted` });
});

// ═══════════════════════════════════════════
//   2. SCRAPE JOB OPERATIONS
// ═══════════════════════════════════════════

// @desc    Trigger a scrape job
// @route   POST /api/admin/scraping/trigger
const triggerScrape = asyncHandler(async (req, res) => {
    const { sourceIds, type, location, priceMin, priceMax, maxPages } = req.body;

    if (!sourceIds || sourceIds.length === 0) {
        res.status(400);
        throw new Error('At least one source must be selected');
    }

    const sources = await ScrapingSource.find({
        _id: { $in: sourceIds },
        isEnabled: true,
    });

    if (sources.length === 0) {
        res.status(400);
        throw new Error('No enabled sources found');
    }

    // Create job record
    const job = await ScrapeJob.create({
        triggeredBy: req.user.id,
        sources: sources.map(s => s.slug),
        type: type || 'incremental',
        status: 'running',
        locationFilter: location,
        priceRangeFilter: { min: priceMin, max: priceMax },
        maxPages: maxPages || 3,
    });

    // Run scrapers asynchronously
    (async () => {
        try {
            const scraperInput = {
                sources: sources.map(s => ({
                    slug: s.slug,
                    script: s.scraperScript,
                    config: {
                        maxPages: maxPages || s.config.maxPages || 3,
                        rateLimit: s.config.rateLimit || 2000,
                        location: location || s.config.defaultLocation || '',
                        priceMin: priceMin || 0,
                        priceMax: priceMax || 0,
                    },
                })),
                type: type || 'incremental',
            };

            const result = await runScraperScript('scraper_runner.py', scraperInput);
            const listings = result?.combined?.listings || [];

            let newCount = 0, updatedCount = 0, dupCount = 0, piiCount = 0;

            // Process each listing
            for (const listing of listings) {
                try {
                    const sourceSlug = listing._sourceSlug || '';
                    const sourceObj = sources.find(s => s.slug === sourceSlug) || sources[0];

                    // Check for duplicate
                    const existing = await ScrapedListing.findOne({ sourceUrl: listing.sourceUrl });
                    if (existing) {
                        // Update if recheck
                        if (type === 'recheck') {
                            existing.lastChecked = new Date();
                            existing.isActive = true;
                            await existing.save();
                            updatedCount++;
                        } else {
                            dupCount++;
                        }
                        continue;
                    }

                    // Get local stats for AI analysis
                    const localStats = await getLocalStats(listing.location?.town);

                    // Run AI analysis
                    let aiAnalysis = {};
                    try {
                        aiAnalysis = await aiService.executeScript('scraped_analyzer.py', {
                            listing,
                            localStats,
                        });
                    } catch (aiErr) {
                        // AI failure shouldn't block listing storage
                        console.error('AI analysis failed:', aiErr.message);
                    }

                    // PII detection
                    if (listing.piiDetected) piiCount++;

                    // Create scraped listing
                    await ScrapedListing.create({
                        source: sourceObj._id,
                        sourceWebsite: sourceObj.name,
                        sourceUrl: listing.sourceUrl,
                        sourceId: listing.sourceId,
                        title: listing.title,
                        description: listing.description,
                        price: listing.price,
                        location: listing.location,
                        beds: listing.beds,
                        baths: listing.baths,
                        size: listing.size,
                        type: listing.type,
                        furnished: listing.furnished,
                        images: listing.images,
                        piiDetected: listing.piiDetected,
                        piiDetails: listing.piiDetails,
                        adminStatus: listing.piiDetected ? 'flagged' : 'pending',
                        aiAnalysis: {
                            estimatedFairPrice: aiAnalysis.estimatedFairPrice || 0,
                            priceRating: aiAnalysis.priceRating || 'Unknown',
                            qualityScore: aiAnalysis.qualityScore || 0,
                            scamRiskScore: aiAnalysis.scamRiskScore || 0,
                            locationInsights: aiAnalysis.locationInsights || '',
                            comparisonToLocal: aiAnalysis.comparisonToLocal || '',
                            tags: aiAnalysis.tags || [],
                            marketTrend: aiAnalysis.marketTrend || 'Unknown',
                            dataCompleteness: aiAnalysis.dataCompleteness || 0,
                            analyzedAt: new Date(),
                        },
                    });
                    newCount++;
                } catch (listingErr) {
                    console.error('Failed to process listing:', listingErr.message);
                }
            }

            // Update job
            job.status = 'completed';
            job.completedAt = new Date();
            job.stats = {
                totalScraped: listings.length,
                newListings: newCount,
                updated: updatedCount,
                duplicatesSkipped: dupCount,
                piiAutoFlagged: piiCount,
            };
            job.errorDetails = result?.errors || [];
            await job.save();

            // Update source health
            for (const source of sources) {
                source.health.lastScrapeAt = new Date();
                source.health.lastSuccessAt = new Date();
                source.health.totalScraped = (source.health.totalScraped || 0) + newCount;
                await source.save();
            }

        } catch (err) {
            job.status = 'failed';
            job.completedAt = new Date();
            job.errorDetails = [{ source: 'runner', message: err.message }];
            await job.save();

            for (const source of sources) {
                source.health.lastScrapeAt = new Date();
                source.health.lastFailureAt = new Date();
                await source.save();
            }
        }
    })();

    res.status(202).json({
        message: 'Scrape job started',
        job,
    });
});

// Helper: get local listing stats for a town
async function getLocalStats(town) {
    if (!town) return { avgPrice: 0, totalListings: 0, avgBeds: 2, avgBaths: 1 };

    const stats = await Listing.aggregate([
        { $match: { 'location.town': { $regex: new RegExp(town, 'i') }, status: 'approved' } },
        {
            $group: {
                _id: null,
                avgPrice: { $avg: '$price' },
                totalListings: { $sum: 1 },
                avgBeds: { $avg: '$beds' },
                avgBaths: { $avg: '$baths' },
            },
        },
    ]);

    if (stats.length > 0) {
        return {
            avgPrice: Math.round(stats[0].avgPrice || 0),
            totalListings: stats[0].totalListings || 0,
            avgBeds: Math.round(stats[0].avgBeds || 2),
            avgBaths: Math.round(stats[0].avgBaths || 1),
        };
    }
    return { avgPrice: 0, totalListings: 0, avgBeds: 2, avgBaths: 1 };
}

// @desc    Get scrape job history
// @route   GET /api/admin/scraping/jobs
const getJobs = asyncHandler(async (req, res) => {
    const { page = 1, limit = 20 } = req.query;
    const jobs = await ScrapeJob.find()
        .populate('triggeredBy', 'name email')
        .sort({ startedAt: -1 })
        .skip((page - 1) * limit)
        .limit(parseInt(limit));

    const total = await ScrapeJob.countDocuments();
    res.status(200).json({ jobs, total, page: parseInt(page), pages: Math.ceil(total / limit) });
});

// @desc    Get specific job details
// @route   GET /api/admin/scraping/jobs/:id
const getJobDetail = asyncHandler(async (req, res) => {
    const job = await ScrapeJob.findById(req.params.id).populate('triggeredBy', 'name email');
    if (!job) {
        res.status(404);
        throw new Error('Job not found');
    }
    res.status(200).json(job);
});

// @desc    Stop a running job
// @route   POST /api/admin/scraping/jobs/:id/stop
const stopJob = asyncHandler(async (req, res) => {
    const job = await ScrapeJob.findById(req.params.id);
    if (!job) {
        res.status(404);
        throw new Error('Job not found');
    }
    if (job.status !== 'running') {
        res.status(400);
        throw new Error('Job is not running');
    }
    job.status = 'stopped';
    job.stoppedBy = req.user.id;
    job.completedAt = new Date();
    await job.save();

    res.status(200).json({ message: 'Job stopped', job });
});

// ═══════════════════════════════════════════
//   3. SCRAPED LISTING MODERATION
// ═══════════════════════════════════════════

// @desc    Get all scraped listings (paginated, filterable)
// @route   GET /api/admin/scraping/listings
const getScrapedListings = asyncHandler(async (req, res) => {
    const {
        page = 1, limit = 20,
        status, source, town, minPrice, maxPrice,
        minQuality, maxScamRisk, search, sort = '-scrapedAt',
    } = req.query;

    let query = {};
    if (status) query.adminStatus = status;
    if (source) query.sourceWebsite = { $regex: new RegExp(source, 'i') };
    if (town) query['location.town'] = { $regex: new RegExp(town, 'i') };
    if (minPrice || maxPrice) {
        query.price = {};
        if (minPrice) query.price.$gte = parseInt(minPrice);
        if (maxPrice) query.price.$lte = parseInt(maxPrice);
    }
    if (minQuality) query['aiAnalysis.qualityScore'] = { $gte: parseInt(minQuality) };
    if (maxScamRisk) query['aiAnalysis.scamRiskScore'] = { $lte: parseInt(maxScamRisk) };
    if (search) {
        const escapeRegex = (text) => text.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&');
        const safeSearch = escapeRegex(search);
        query.$or = [
            { title: { $regex: new RegExp(safeSearch, 'i') } },
            { description: { $regex: new RegExp(safeSearch, 'i') } },
        ];
    }

    const listings = await ScrapedListing.find(query)
        .sort(sort)
        .skip((page - 1) * limit)
        .limit(parseInt(limit));

    const total = await ScrapedListing.countDocuments(query);

    // Status counts
    const statusCounts = await ScrapedListing.aggregate([
        { $group: { _id: '$adminStatus', count: { $sum: 1 } } },
    ]);

    res.status(200).json({
        listings,
        total,
        page: parseInt(page),
        pages: Math.ceil(total / limit),
        statusCounts: statusCounts.reduce((acc, s) => { acc[s._id] = s.count; return acc; }, {}),
    });
});

// @desc    Get single scraped listing
// @route   GET /api/admin/scraping/listings/:id
const getScrapedListing = asyncHandler(async (req, res) => {
    const listing = await ScrapedListing.findById(req.params.id).populate('source', 'name slug url');
    if (!listing) {
        res.status(404);
        throw new Error('Scraped listing not found');
    }
    res.status(200).json(listing);
});

// @desc    Edit scraped listing fields
// @route   PUT /api/admin/scraping/listings/:id
const editScrapedListing = asyncHandler(async (req, res) => {
    const listing = await ScrapedListing.findById(req.params.id);
    if (!listing) {
        res.status(404);
        throw new Error('Scraped listing not found');
    }

    const { beds, baths, type, location, furnished, adminNotes, showFullDescription, showImages } = req.body;
    if (beds !== undefined) listing.beds = beds;
    if (baths !== undefined) listing.baths = baths;
    if (type !== undefined) listing.type = type;
    if (location !== undefined) listing.location = { ...listing.location.toObject?.() || listing.location, ...location };
    if (furnished !== undefined) listing.furnished = furnished;
    if (adminNotes !== undefined) listing.adminNotes = adminNotes;
    if (showFullDescription !== undefined) listing.showFullDescription = showFullDescription;
    if (showImages !== undefined) listing.showImages = showImages;

    await listing.save();
    res.status(200).json(listing);
});

// @desc    Approve scraped listing
// @route   PUT /api/admin/scraping/listings/:id/approve
const approveScrapedListing = asyncHandler(async (req, res) => {
    const listing = await ScrapedListing.findById(req.params.id);
    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }
    listing.adminStatus = 'approved';
    listing.reviewedBy = req.user.id;
    listing.reviewedAt = new Date();
    await listing.save();
    res.status(200).json({ message: 'Listing approved', listing });
});

// @desc    Hide scraped listing
// @route   PUT /api/admin/scraping/listings/:id/hide
const hideScrapedListing = asyncHandler(async (req, res) => {
    const listing = await ScrapedListing.findById(req.params.id);
    if (!listing) { res.status(404); throw new Error('Listing not found'); }
    listing.adminStatus = 'hidden';
    listing.reviewedBy = req.user.id;
    listing.reviewedAt = new Date();
    if (req.body.notes) listing.adminNotes = req.body.notes;
    await listing.save();
    res.status(200).json({ message: 'Listing hidden', listing });
});

// @desc    Flag scraped listing
// @route   PUT /api/admin/scraping/listings/:id/flag
const flagScrapedListing = asyncHandler(async (req, res) => {
    const listing = await ScrapedListing.findById(req.params.id);
    if (!listing) { res.status(404); throw new Error('Listing not found'); }
    listing.adminStatus = 'flagged';
    listing.reviewedBy = req.user.id;
    listing.reviewedAt = new Date();
    if (req.body.notes) listing.adminNotes = req.body.notes;
    await listing.save();
    res.status(200).json({ message: 'Listing flagged', listing });
});

// @desc    Assign listing to admin
// @route   PUT /api/admin/scraping/listings/:id/assign
const assignScrapedListing = asyncHandler(async (req, res) => {
    const listing = await ScrapedListing.findById(req.params.id);
    if (!listing) { res.status(404); throw new Error('Listing not found'); }
    listing.assignedTo = req.body.adminId;
    await listing.save();
    res.status(200).json({ message: 'Listing assigned', listing });
});

// @desc    Re-run AI analysis
// @route   POST /api/admin/scraping/listings/:id/analyze
const reAnalyzeListing = asyncHandler(async (req, res) => {
    const listing = await ScrapedListing.findById(req.params.id);
    if (!listing) { res.status(404); throw new Error('Listing not found'); }

    const localStats = await getLocalStats(listing.location?.town);
    const aiResult = await aiService.executeScript('scraped_analyzer.py', {
        listing: listing.toObject(),
        localStats,
    });

    listing.aiAnalysis = {
        estimatedFairPrice: aiResult.estimatedFairPrice || 0,
        priceRating: aiResult.priceRating || 'Unknown',
        qualityScore: aiResult.qualityScore || 0,
        scamRiskScore: aiResult.scamRiskScore || 0,
        locationInsights: aiResult.locationInsights || '',
        comparisonToLocal: aiResult.comparisonToLocal || '',
        tags: aiResult.tags || [],
        marketTrend: aiResult.marketTrend || 'Unknown',
        dataCompleteness: aiResult.dataCompleteness || 0,
        analyzedAt: new Date(),
    };
    await listing.save();

    res.status(200).json({ message: 'Analysis updated', listing });
});

// @desc    Bulk actions on scraped listings
// @route   POST /api/admin/scraping/listings/bulk
const bulkAction = asyncHandler(async (req, res) => {
    const { action, listingIds, sourceId } = req.body;

    let filter = {};
    if (listingIds && listingIds.length > 0) {
        filter._id = { $in: listingIds };
    } else if (sourceId) {
        filter.source = sourceId;
    } else {
        res.status(400);
        throw new Error('Provide listingIds or sourceId');
    }

    let update = {};
    switch (action) {
        case 'approve':
            update = { adminStatus: 'approved', reviewedBy: req.user.id, reviewedAt: new Date() };
            break;
        case 'hide':
            update = { adminStatus: 'hidden', reviewedBy: req.user.id, reviewedAt: new Date() };
            break;
        case 'flag':
            update = { adminStatus: 'flagged', reviewedBy: req.user.id, reviewedAt: new Date() };
            break;
        case 'delete':
            const delResult = await ScrapedListing.deleteMany(filter);
            return res.status(200).json({ message: `${delResult.deletedCount} listings deleted` });
        default:
            res.status(400);
            throw new Error('Invalid action. Use: approve, hide, flag, delete');
    }

    const result = await ScrapedListing.updateMany(filter, { $set: update });
    res.status(200).json({ message: `${result.modifiedCount} listings ${action}d` });
});

// ═══════════════════════════════════════════
//   4. HEALTH & STATS
// ═══════════════════════════════════════════

// @desc    Get scraping health dashboard
// @route   GET /api/admin/scraping/health
const getHealth = asyncHandler(async (req, res) => {
    const sources = await ScrapingSource.find();
    const totalScraped = await ScrapedListing.countDocuments();
    const todayStart = new Date(); todayStart.setHours(0, 0, 0, 0);
    const newToday = await ScrapedListing.countDocuments({ scrapedAt: { $gte: todayStart } });
    const piiCount = await ScrapedListing.countDocuments({ piiDetected: true, adminStatus: { $ne: 'hidden' } });
    const pendingCount = await ScrapedListing.countDocuments({ adminStatus: 'pending' });

    const recentJob = await ScrapeJob.findOne().sort({ startedAt: -1 });

    res.status(200).json({
        totalScraped,
        newToday,
        piiAlerts: piiCount,
        pending: pendingCount,
        sourcesActive: sources.filter(s => s.isEnabled).length,
        sourcesBlocked: sources.filter(s => s.health?.isBlocked).length,
        lastScrape: recentJob?.startedAt,
        sources: sources.map(s => ({
            id: s._id,
            name: s.name,
            slug: s.slug,
            status: s.status,
            isEnabled: s.isEnabled,
            health: s.health,
            schedule: s.schedule,
        })),
    });
});

// @desc    Get scraping stats
// @route   GET /api/admin/scraping/stats
const getScrapingStats = asyncHandler(async (req, res) => {
    const byStatus = await ScrapedListing.aggregate([
        { $group: { _id: '$adminStatus', count: { $sum: 1 } } },
    ]);
    const bySource = await ScrapedListing.aggregate([
        { $group: { _id: '$sourceWebsite', count: { $sum: 1 }, avgPrice: { $avg: '$price' } } },
    ]);
    const byTown = await ScrapedListing.aggregate([
        { $group: { _id: '$location.town', count: { $sum: 1 }, avgPrice: { $avg: '$price' } } },
        { $sort: { count: -1 } },
        { $limit: 20 },
    ]);

    res.status(200).json({ byStatus, bySource, byTown });
});

// ═══════════════════════════════════════════
//   5. MARKET INTELLIGENCE
// ═══════════════════════════════════════════

// @desc    Get market intelligence report
// @route   GET /api/admin/scraping/market-report
const getMarketReport = asyncHandler(async (req, res) => {
    // Scraped data by area
    const scrapedByArea = await ScrapedListing.aggregate([
        { $match: { adminStatus: { $ne: 'hidden' } } },
        { $group: { _id: '$location.town', count: { $sum: 1 }, avgPrice: { $avg: '$price' }, sources: { $addToSet: '$sourceWebsite' } } },
        { $project: { town: '$_id', count: 1, avgPrice: 1, sources: 1, _id: 0 } },
    ]);

    // Local data by area
    const localByArea = await Listing.aggregate([
        { $match: { status: 'approved' } },
        { $group: { _id: '$location.town', count: { $sum: 1 }, avgPrice: { $avg: '$price' } } },
        { $project: { town: '$_id', count: 1, avgPrice: 1, _id: 0 } },
    ]);

    // By source
    const scrapedBySource = await ScrapedListing.aggregate([
        { $group: { _id: '$sourceWebsite', count: { $sum: 1 }, avgPrice: { $avg: '$price' } } },
        { $project: { source: '$_id', count: 1, avgPrice: 1, _id: 0 } },
    ]);

    const totalScraped = await ScrapedListing.countDocuments();
    const totalLocal = await Listing.countDocuments({ status: 'approved' });

    const report = await aiService.executeScript('market_intelligence.py', {
        scrapedByArea, localByArea, scrapedBySource, totalScraped, totalLocal,
    });

    res.status(200).json(report);
});

// @desc    Get price comparison data
// @route   GET /api/admin/scraping/price-comparison
const getPriceComparison = asyncHandler(async (req, res) => {
    const scrapedByArea = await ScrapedListing.aggregate([
        { $match: { price: { $gt: 0 }, adminStatus: { $ne: 'hidden' } } },
        { $group: { _id: '$location.town', scrapedAvg: { $avg: '$price' }, scrapedCount: { $sum: 1 } } },
    ]);

    const localByArea = await Listing.aggregate([
        { $match: { price: { $gt: 0 }, status: 'approved' } },
        { $group: { _id: '$location.town', localAvg: { $avg: '$price' }, localCount: { $sum: 1 } } },
    ]);

    const localMap = {};
    localByArea.forEach(l => { localMap[l._id?.toLowerCase()] = l; });

    const comparison = scrapedByArea.map(s => {
        const local = localMap[s._id?.toLowerCase()] || {};
        const diff = local.localAvg ? ((s.scrapedAvg - local.localAvg) / local.localAvg * 100) : 0;
        return {
            town: s._id,
            scrapedAvg: Math.round(s.scrapedAvg),
            localAvg: Math.round(local.localAvg || 0),
            diffPercent: Math.round(diff),
            scrapedCount: s.scrapedCount,
            localCount: local.localCount || 0,
        };
    }).sort((a, b) => Math.abs(b.diffPercent) - Math.abs(a.diffPercent));

    res.status(200).json(comparison);
});

// @desc    Get hot areas
// @route   GET /api/admin/scraping/hot-areas
const getHotAreas = asyncHandler(async (req, res) => {
    const areas = await ScrapedListing.aggregate([
        { $match: { adminStatus: { $ne: 'hidden' } } },
        { $group: { _id: '$location.town', count: { $sum: 1 }, avgPrice: { $avg: '$price' }, totalViews: { $sum: '$views' } } },
        { $sort: { count: -1 } },
        { $limit: 20 },
    ]);

    res.status(200).json(areas.map(a => ({
        town: a._id,
        listingCount: a.count,
        avgPrice: Math.round(a.avgPrice),
        totalViews: a.totalViews,
    })));
});

// @desc    Get data quality by source
// @route   GET /api/admin/scraping/data-quality
const getDataQuality = asyncHandler(async (req, res) => {
    const sources = await ScrapedListing.aggregate([
        {
            $group: {
                _id: '$sourceWebsite',
                total: { $sum: 1 },
                withBeds: { $sum: { $cond: [{ $gt: ['$beds', 0] }, 1, 0] } },
                withBaths: { $sum: { $cond: [{ $gt: ['$baths', 0] }, 1, 0] } },
                withImages: { $sum: { $cond: [{ $gt: [{ $size: { $ifNull: ['$images', []] } }, 0] }, 1, 0] } },
                withTown: { $sum: { $cond: [{ $gt: [{ $strLenCP: { $ifNull: ['$location.town', ''] } }, 0] }, 1, 0] } },
                avgQuality: { $avg: '$aiAnalysis.qualityScore' },
                avgCompleteness: { $avg: '$aiAnalysis.dataCompleteness' },
            },
        },
    ]);

    res.status(200).json(sources.map(s => ({
        source: s._id,
        total: s.total,
        bedsPercent: Math.round((s.withBeds / s.total) * 100),
        bathsPercent: Math.round((s.withBaths / s.total) * 100),
        imagesPercent: Math.round((s.withImages / s.total) * 100),
        townPercent: Math.round((s.withTown / s.total) * 100),
        avgQuality: Math.round(s.avgQuality || 0),
        avgCompleteness: Math.round(s.avgCompleteness || 0),
    })));
});

// ═══════════════════════════════════════════
//   6. EXPOSURE & CONVERSION
// ═══════════════════════════════════════════

// @desc    Get/Set exposure rules
// @route   GET/PUT /api/admin/scraping/exposure-rules
const getExposureRules = asyncHandler(async (req, res) => {
    // For now, return defaults. In production, store in a settings collection.
    res.status(200).json({
        maxExternalPercent: 20,
        boostInternalAlways: true,
        showDescriptionSnippetOnly: true,
        showImages: true,
        forceSourceLink: true,
        autoExpireDays: 30,
    });
});

// @desc    Get conversion stats
// @route   GET /api/admin/scraping/conversion-stats
const getConversionStats = asyncHandler(async (req, res) => {
    const totalViews = await ScrapedListing.aggregate([
        { $group: { _id: null, views: { $sum: '$views' }, clicks: { $sum: '$clickThroughs' } } },
    ]);

    const stats = totalViews[0] || { views: 0, clicks: 0 };

    res.status(200).json({
        externalViews: stats.views,
        clickThroughs: stats.clicks,
        clickRate: stats.views > 0 ? Math.round((stats.clicks / stats.views) * 100) : 0,
    });
});

// ═══════════════════════════════════════════
//   7. PUBLIC API
// ═══════════════════════════════════════════

// @desc    Get approved external listings (public)
// @route   GET /api/scraping/external-listings
const getExternalListings = asyncHandler(async (req, res) => {
    const {
        page = 1, limit = 20,
        town, minPrice, maxPrice, beds, type, sort = '-scrapedAt',
    } = req.query;

    let query = { adminStatus: 'approved', isActive: true };
    if (town) query['location.town'] = { $regex: new RegExp(town, 'i') };
    if (beds) query.beds = parseInt(beds);
    if (type) query.type = type;
    if (minPrice || maxPrice) {
        query.price = {};
        if (minPrice) query.price.$gte = parseInt(minPrice);
        if (maxPrice) query.price.$lte = parseInt(maxPrice);
    }

    const listings = await ScrapedListing.find(query)
        .select('-adminNotes -assignedTo -reviewedBy -piiDetails')
        .sort(sort)
        .skip((page - 1) * limit)
        .limit(parseInt(limit));

    const total = await ScrapedListing.countDocuments(query);

    // Track views
    if (listings.length > 0) {
        await ScrapedListing.updateMany(
            { _id: { $in: listings.map(l => l._id) } },
            { $inc: { views: 1 } }
        );
    }

    res.status(200).json({
        listings,
        total,
        page: parseInt(page),
        pages: Math.ceil(total / limit),
    });
});

// @desc    Track click-through to external source
// @route   POST /api/scraping/external-listings/:id/click
const trackClickThrough = asyncHandler(async (req, res) => {
    await ScrapedListing.findByIdAndUpdate(req.params.id, { $inc: { clickThroughs: 1 } });
    res.status(200).json({ message: 'Click tracked' });
});

module.exports = {
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
};
