const asyncHandler = require('express-async-handler');
const Inquiry = require('../models/Inquiry');
const Listing = require('../models/Listing');
const { createNotification } = require('./notificationController');

// @desc    Send inquiry on a listing
// @route   POST /api/inquiries
// @access  Private
const sendInquiry = asyncHandler(async (req, res) => {
    const { listingId, message } = req.body;

    if (!listingId || !message) {
        res.status(400);
        throw new Error('Listing ID and message are required');
    }

    const listing = await Listing.findById(listingId);
    if (!listing) {
        res.status(404);
        throw new Error('Listing not found');
    }

    if (listing.owner.toString() === req.user.id) {
        res.status(400);
        throw new Error('You cannot send an inquiry on your own listing');
    }

    const inquiry = await Inquiry.create({
        listing: listingId,
        sender: req.user.id,
        owner: listing.owner,
        message,
    });

    // Notify the owner
    await createNotification({
        userId: listing.owner,
        type: 'inquiry_received',
        title: 'New Inquiry',
        message: `${req.user.name} sent an inquiry about "${listing.title}"`,
        link: `/inbox`,
    });

    const populated = await Inquiry.findById(inquiry._id)
        .populate('sender', 'name email avatar')
        .populate('listing', 'title images price');

    res.status(201).json(populated);
});

// @desc    Get received inquiries (for listing owners)
// @route   GET /api/inquiries/received
// @access  Private
const getReceivedInquiries = asyncHandler(async (req, res) => {
    const inquiries = await Inquiry.find({ owner: req.user.id })
        .populate('sender', 'name email avatar phone')
        .populate('listing', 'title images price location')
        .sort({ createdAt: -1 });
    res.status(200).json(inquiries);
});

// @desc    Get sent inquiries (for renters)
// @route   GET /api/inquiries/sent
// @access  Private
const getSentInquiries = asyncHandler(async (req, res) => {
    const inquiries = await Inquiry.find({ sender: req.user.id })
        .populate('owner', 'name email avatar')
        .populate('listing', 'title images price location')
        .sort({ createdAt: -1 });
    res.status(200).json(inquiries);
});

// @desc    Get single inquiry with replies
// @route   GET /api/inquiries/:id
// @access  Private
const getInquiry = asyncHandler(async (req, res) => {
    const inquiry = await Inquiry.findById(req.params.id)
        .populate('sender', 'name email avatar phone')
        .populate('owner', 'name email avatar phone')
        .populate('listing', 'title images price location')
        .populate('replies.sender', 'name avatar');

    if (!inquiry) {
        res.status(404);
        throw new Error('Inquiry not found');
    }

    // Only sender or owner can view
    if (inquiry.sender._id.toString() !== req.user.id && inquiry.owner._id.toString() !== req.user.id) {
        res.status(401);
        throw new Error('Not authorized');
    }

    // Mark as read if owner is viewing
    if (inquiry.owner._id.toString() === req.user.id && inquiry.status === 'new') {
        inquiry.status = 'read';
        await inquiry.save();
    }

    res.status(200).json(inquiry);
});

// @desc    Reply to an inquiry
// @route   POST /api/inquiries/:id/reply
// @access  Private
const replyToInquiry = asyncHandler(async (req, res) => {
    const { message } = req.body;

    if (!message) {
        res.status(400);
        throw new Error('Message is required');
    }

    const inquiry = await Inquiry.findById(req.params.id);

    if (!inquiry) {
        res.status(404);
        throw new Error('Inquiry not found');
    }

    // Only sender or owner can reply
    if (inquiry.sender.toString() !== req.user.id && inquiry.owner.toString() !== req.user.id) {
        res.status(401);
        throw new Error('Not authorized');
    }

    inquiry.replies.push({
        sender: req.user.id,
        message,
    });

    // Update status
    if (inquiry.owner.toString() === req.user.id) {
        inquiry.status = 'replied';
    }

    await inquiry.save();

    // Notify the other party
    const recipientId = inquiry.owner.toString() === req.user.id
        ? inquiry.sender
        : inquiry.owner;

    await createNotification({
        userId: recipientId,
        type: 'inquiry_reply',
        title: 'New Reply',
        message: `${req.user.name} replied to your inquiry`,
        link: `/inbox`,
    });

    const populated = await Inquiry.findById(inquiry._id)
        .populate('sender', 'name email avatar phone')
        .populate('owner', 'name email avatar phone')
        .populate('listing', 'title images price location')
        .populate('replies.sender', 'name avatar');

    res.status(200).json(populated);
});

// @desc    Close inquiry
// @route   PUT /api/inquiries/:id/close
// @access  Private
const closeInquiry = asyncHandler(async (req, res) => {
    const inquiry = await Inquiry.findById(req.params.id);

    if (!inquiry) {
        res.status(404);
        throw new Error('Inquiry not found');
    }

    if (inquiry.owner.toString() !== req.user.id) {
        res.status(401);
        throw new Error('Only the listing owner can close an inquiry');
    }

    inquiry.status = 'closed';
    await inquiry.save();

    res.status(200).json(inquiry);
});

module.exports = {
    sendInquiry,
    getReceivedInquiries,
    getSentInquiries,
    getInquiry,
    replyToInquiry,
    closeInquiry,
};
