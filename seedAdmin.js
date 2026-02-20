const mongoose = require('mongoose');
const dotenv = require('dotenv');
const User = require('./models/User');

dotenv.config();

const seedAdmin = async () => {
    try {
        const conn = await mongoose.connect(process.env.MONGO_URI);
        console.log(`MongoDB Connected: ${conn.connection.host}`);

        // Check if admin already exists
        const adminExists = await User.findOne({ email: 'admin@houserentlk.com' });

        if (adminExists) {
            console.log('Admin user already exists');
            process.exit();
        }

        // Create admin user
        const user = await User.create({
            name: 'Super Admin',
            email: 'admin@houserentlk.com',
            password: 'adminpassword123', // Will be hashed by pre-save hook
            role: 'admin',
            phone: '+94 77 000 0000',
            bio: 'System Administrator',
            isVerified: true
        });

        console.log('Admin user created successfully');
        console.log('Email: admin@houserentlk.com');
        console.log('Password: adminpassword123');

        process.exit();
    } catch (error) {
        console.error(`Error: ${error.message}`);
        process.exit(1);
    }
};

seedAdmin();
