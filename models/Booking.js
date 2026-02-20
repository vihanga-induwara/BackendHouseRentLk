const mongoose = require('mongoose');

const bookingSchema = new mongoose.Schema({
    listing: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Listing',
        required: true
    },
    renter: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true
    },
    owner: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true
    },
    date: {
        type: Date,
        required: true
    },
    timeSlot: {
        type: String,
        required: true
    },
    status: {
        type: String,
        enum: ['pending', 'confirmed', 'rejected', 'completed', 'cancelled'],
        default: 'pending'
    },
    message: String,
    notes: String
}, {
    timestamps: true
});

// Prevent double bookings: A listing cannot be booked for the same date & time slot twice
bookingSchema.index({ listing: 1, date: 1, timeSlot: 1 }, { unique: true });


module.exports = mongoose.model('Booking', bookingSchema);
