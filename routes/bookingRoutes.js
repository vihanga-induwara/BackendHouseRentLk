const express = require('express');
const router = express.Router();
const { protect } = require('../middleware/authMiddleware');
const {
    createBooking,
    getMyBookings,
    updateBookingStatus
} = require('../controllers/bookingController');

router.route('/')
    .post(protect, createBooking)
    .get(protect, getMyBookings);

router.route('/:id/status')
    .put(protect, updateBookingStatus);

module.exports = router;
