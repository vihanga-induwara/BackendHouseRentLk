jest.setTimeout(30000); // 30s timeout

beforeAll(async () => {
    process.env.JWT_SECRET = 'test_secret';
    process.env.NODE_ENV = 'test';
});

afterAll(async () => {
    // cleanup
});
