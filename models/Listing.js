const mongoose = require('mongoose');

const listingSchema = mongoose.Schema(
    {
        owner: {
            type: mongoose.Schema.ObjectId,
            ref: 'User',
            required: true,
        },
        title: {
            type: String,
            required: [true, 'Please add a title'],
            trim: true,
            maxlength: [100, 'Title cannot be more than 100 characters'],
        },
        description: {
            type: String,
            required: [true, 'Please add a description'],
            maxlength: [2000, 'Description cannot be more than 2000 characters'],
        },
        type: {
            type: String,
            required: true,
            enum: ['House', 'Boarding Room', 'Annex', 'Apartment', 'Other'],
        },
        // Location Info
        location: {
            town: { type: String, required: true },
            street: { type: String, required: true },
            houseNumber: { type: String },
            address: { type: String, required: true }, // Full address string
            // GeoJSON Point for Maps
            coordinates: {
                type: { type: String, enum: ['Point'], default: 'Point' },
                coordinates: { type: [Number], index: '2dsphere' }, // [lng, lat]
            },
        },
        // Rental Details
        price: {
            type: Number,
            required: [true, 'Please add a price'],
        },
        negotiable: {
            type: Boolean,
            default: false,
        },
        advancePayment: {
            type: Number, // Number of months
            default: 0,
        },
        minRentalPeriod: {
            type: Number, // Number of months
            default: 1,
        },
        // Specs
        beds: { type: Number, required: true },
        baths: { type: Number, required: true },
        size: { type: Number, required: true }, // Sqft
        furnished: { type: String, enum: ['Furnished', 'Unfurnished', 'Semi-Furnished'], default: 'Unfurnished' },

        // Facilities & Amenities
        amenities: {
            solarPower: { type: Boolean, default: false },
            ac: { type: Boolean, default: false },
            parking: { type: Boolean, default: false },
            wifi: { type: Boolean, default: false },
            attachedBath: { type: Boolean, default: false },
            petsAllowed: { type: Boolean, default: false },
            security: { type: Boolean, default: false },
            garden: { type: Boolean, default: false },
            waterSupply: { type: String, enum: ['Tap', 'Well', 'Both'], default: 'Tap' },
            servantQuarters: { type: Boolean, default: false },
            templeDistance: { type: Number }, // km
            mainRoadDistance: { type: Number }, // km
        },

        // Media
        images: {
            type: [String], // URLs
            validate: [arrayLimit, '{PATH} exceeds the limit of 10'],
        },
        video: {
            type: String, // URL
        },
        virtualTourUrl: {
            type: String, // URL for 360 tour
        },

        // Additional Info
        isUrgent: { type: Boolean, default: false },
        agreementRequired: { type: Boolean, default: false },
        availableFrom: { type: Date, default: Date.now },
        tenantType: { type: String, enum: ['Family', 'Students', 'Professionals', 'Any'], default: 'Any' },
        houseRules: { type: String },
        availableVisits: [
            {
                day: { type: String, enum: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Daily', 'Weekdays', 'Weekends'] },
                times: { type: String } // e.g., "9 AM - 12 PM"
            }
        ],

        // System
        status: {
            type: String,
            enum: ['pending', 'approved', 'rejected', 'changes_requested', 'paused', 'rented', 'expired'],
            default: 'pending',
        },
        views: {
            type: Number,
            default: 0,
        },
        shares: {
            type: Number,
            default: 0,
        },
        // Contact Details
        contactDetails: {
            phone2: { type: String },
            whatsapp: { type: String },
            whatsappMsg: { type: String, default: "Hi, I'm interested in this property." },
            availableTimes: { type: String }, // e.g., "Weekdays 9 AM - 5 PM"
            email: { type: String }, // Optional override
        },
        // AI Generated Content
        aiDescription: {
            description: { type: String },
            townVibe: { type: String },
            generatedAt: { type: Date },
        },
        aiTitle: {
            title: { type: String },
            alternatives: [String],
            generatedAt: { type: Date },
        },
        autoTags: {
            type: [String],
            default: [],
        },
        nearbyPlaces: {
            type: [String],
            default: [],
        },
        expiresAt: {
            type: Date,
        },
        renewedAt: {
            type: Date,
        },
        isGoodDeal: {
            type: Boolean,
            default: false,
        },
    },
    {
        timestamps: true,
    }
);

function arrayLimit(val) {
    return val.length <= 10;
}

// Virtual for "New" badge (less than 7 days old)
listingSchema.virtual('isNewListing').get(function () {
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    return this.createdAt > sevenDaysAgo;
});

// Ensure virtuals are serialized
listingSchema.set('toJSON', { virtuals: true });
listingSchema.set('toObject', { virtuals: true });

listingSchema.index({ 'location.coordinates': '2dsphere' });
listingSchema.index({ status: 1, type: 1, price: 1 }); // Optimize common search filters


module.exports = mongoose.model('Listing', listingSchema);
