const asyncHandler = require('express-async-handler');
const Booking = require('../models/Booking');
const Listing = require('../models/Listing');

// @desc    Create a new booking request
// @route   POST /api/bookings
// @access  Private
const createBooking = asyncHandler(async (req, res) => {
    const { listingId, date, timeSlot, message } = req.body;

    const listing = await Listing.findById(listingId);
    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    // Check for double booking
    const existingBooking = await Booking.findOne({ listing: listingId, date, timeSlot, status: { $ne: 'cancelled' } });
    if (existingBooking) {
        res.status(400);
        throw new Error('This time slot is already booked');
    }

    const booking = await Booking.create({
        listing: listingId,
        renter: req.user._id,
        owner: listing.owner,
        date,
        timeSlot,
        message
    });

    res.status(201).json(booking);
});

// @desc    Get user's bookings (as renter or owner)
// @route   GET /api/bookings
// @access  Private
const getMyBookings = asyncHandler(async (req, res) => {
    const bookings = await Booking.find({
        $or: [{ renter: req.user._id }, { owner: req.user._id }]
    })
        .populate('listing', 'title images price location')
        .populate('renter', 'name email phone avatar')
        .populate('owner', 'name email phone avatar')
        .sort('-createdAt');

    res.json(bookings);
});

// @desc    Update booking status
// @route   PUT /api/bookings/:id/status
// @access  Private
const updateBookingStatus = asyncHandler(async (req, res) => {
    const { status, notes } = req.body;
    const booking = await Booking.findById(req.params.id);

    if (!booking) {
        res.status(404);
        throw new Error('Booking not found');
    }

    // Check if user is the owner or renter allowed to update this
    if (booking.owner.toString() !== req.user._id.toString() &&
        booking.renter.toString() !== req.user._id.toString()) {
        res.status(401);
        throw new Error('Not authorized to update this booking');
    }

    booking.status = status;
    if (notes) booking.notes = notes;

    await booking.save();
    res.json(booking);
});

module.exports = {
    createBooking,
    getMyBookings,
    updateBookingStatus
};
