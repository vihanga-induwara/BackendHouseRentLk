const { getListings, createListing } = require('../controllers/listingController');
// const Listing = require('../models/Listing'); // Mocked
const aiService = require('../services/aiService'); // Mocked

// Mock dependencies
jest.mock('../models/Listing', () => ({
    find: jest.fn(),
    countDocuments: jest.fn(),
    create: jest.fn(),
}));
jest.mock('../services/aiService', () => ({
    executeScript: jest.fn()
}));
jest.mock('../controllers/notificationController', () => ({
    createNotification: jest.fn()
}));

const Listing = require('../models/Listing'); // Require after mock to get the mocked module

describe('Listing Controller', () => {
    let req, res, next;

    beforeEach(() => {
        req = {
            query: {},
            body: {},
            user: { id: 'user_id', role: 'owner', isEmailVerified: true, isPhoneVerified: true }
        };
        res = {
            status: jest.fn().mockReturnThis(),
            json: jest.fn(),
        };
        next = jest.fn();
        jest.clearAllMocks();
    });

    describe('getListings', () => {
        it('should return listings with pagination', async () => {
            req.query = { page: '1', limit: '10' };
            const mockListings = [{ title: 'Test Listing' }];

            // Mock chainable find().populate().sort().skip().limit()
            const mockFind = {
                populate: jest.fn().mockReturnThis(),
                sort: jest.fn().mockReturnThis(),
                skip: jest.fn().mockReturnThis(),
                limit: jest.fn().mockResolvedValue(mockListings)
            };
            Listing.find.mockReturnValue(mockFind);
            Listing.countDocuments.mockResolvedValue(1);

            // getListings is an async handler wrapper
            // If getListings is wrapped with express-async-handler, exporting it exports the wrapper function (req, res, next) => ...
            // So we can call it directly.

            await getListings(req, res, next);

            expect(res.status).toHaveBeenCalledWith(200);
            expect(res.json).toHaveBeenCalledWith(expect.objectContaining({
                count: 1,
                data: mockListings
            }));
        });
    });

    describe('createListing', () => {
        it('should create a listing successfully', async () => {
            req.body = {
                title: 'New House',
                price: 50000,
                town: 'Colombo'
            };

            const mockAiService = require('../services/aiService');
            mockAiService.executeScript.mockResolvedValue({
                description: 'AI Generated Description',
                townVibe: 'Cool Vibe'
            });

            Listing.create.mockResolvedValue({
                title: 'New House',
                aiDescription: { description: 'AI Generated Description' }
            });

            await createListing(req, res, next);

            expect(Listing.create).toHaveBeenCalled();
            expect(res.status).toHaveBeenCalledWith(201);
        });
    });
});
