const { registerUser, loginUser } = require('../controllers/authController');
const User = require('../models/User');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

// Mock dependencies
jest.mock('../models/User');
jest.mock('bcryptjs');
jest.mock('jsonwebtoken');

describe('Auth Controller', () => {
    let req, res, next;

    beforeEach(() => {
        req = { body: {} };
        res = {
            status: jest.fn().mockReturnThis(),
            json: jest.fn(),
        };
        next = jest.fn();
    });

    describe('registerUser', () => {
        it('should return 400 if fields are missing', async () => {
            req.body = { name: 'Test', email: '' }; // Missing password

            await registerUser(req, res, next);

            expect(res.status).toHaveBeenCalledWith(400);
            expect(next).toHaveBeenCalledWith(expect.any(Error));
            expect(next.mock.calls[0][0].message).toBe('Please add all fields');
        });

        it('should return 400 for invalid email', async () => {
            req.body = { name: 'Test', email: 'invalid-email', password: 'StrongPassword123!' };

            await registerUser(req, res, next);

            expect(res.status).toHaveBeenCalledWith(400);
            expect(next).toHaveBeenCalledWith(expect.any(Error));
            expect(next.mock.calls[0][0].message).toBe('Invalid email format');
        });

        it('should return 400 for weak password', async () => {
            req.body = { name: 'Test', email: 'test@example.com', password: 'weak' };

            await registerUser(req, res, next);

            expect(res.status).toHaveBeenCalledWith(400);
            expect(next).toHaveBeenCalledWith(expect.any(Error));
            expect(next.mock.calls[0][0].message).toBe('Password must be at least 8 characters and include uppercase, lowercase, and numbers.');
        });

        it('should return 400 if user already exists', async () => {
            req.body = { name: 'Test', email: 'test@example.com', password: 'StrongPassword123!' };
            User.findOne.mockResolvedValue({ email: 'test@example.com' });

            await registerUser(req, res, next);

            expect(res.status).toHaveBeenCalledWith(400);
            expect(next).toHaveBeenCalledWith(expect.any(Error));
            expect(next.mock.calls[0][0].message).toBe('User already exists');
        });

        it('should register user successfully', async () => {
            req.body = { name: 'Test', email: 'new@example.com', password: 'StrongPassword123!' };
            User.findOne.mockResolvedValue(null);
            bcrypt.genSalt.mockResolvedValue('salt');
            bcrypt.hash.mockResolvedValue('hashedPassword');
            User.create.mockResolvedValue({
                _id: 'user_id',
                name: 'Test',
                email: 'new@example.com',
                password: 'hashedPassword',
                role: 'renter'
            });
            process.env.JWT_SECRET = 'test_secret';
            jwt.sign = jest.fn().mockReturnValue('test_token');

            await registerUser(req, res, next);

            expect(res.status).toHaveBeenCalledWith(201);
            expect(res.json).toHaveBeenCalledWith(expect.objectContaining({
                name: 'Test',
                token: 'test_token'
            }));
        });
    });
});
