const asyncHandler = require('express-async-handler');
const Notification = require('../models/Notification');

// Helper: Create a notification (used by other controllers)
const createNotification = async ({ userId, type, title, message, link }) => {
    try {
        await Notification.create({ user: userId, type, title, message, link });
    } catch (err) {
        console.error('Failed to create notification:', err.message);
    }
};

// @desc    Get user's notifications
// @route   GET /api/notifications
// @access  Private
const getNotifications = asyncHandler(async (req, res) => {
    const notifications = await Notification.find({ user: req.user.id })
        .sort({ createdAt: -1 })
        .limit(50);
    res.status(200).json(notifications);
});

// @desc    Get unread count
// @route   GET /api/notifications/unread-count
// @access  Private
const getUnreadCount = asyncHandler(async (req, res) => {
    const count = await Notification.countDocuments({ user: req.user.id, read: false });
    res.status(200).json({ count });
});

// @desc    Mark single notification as read
// @route   PUT /api/notifications/:id/read
// @access  Private
const markAsRead = asyncHandler(async (req, res) => {
    const notification = await Notification.findById(req.params.id);

    if (!notification) {
        res.status(404);
        throw new Error('Notification not found');
    }

    if (notification.user.toString() !== req.user.id) {
        res.status(401);
        throw new Error('Not authorized');
    }

    notification.read = true;
    await notification.save();
    res.status(200).json(notification);
});

// @desc    Mark all as read
// @route   PUT /api/notifications/read-all
// @access  Private
const markAllAsRead = asyncHandler(async (req, res) => {
    await Notification.updateMany(
        { user: req.user.id, read: false },
        { read: true }
    );
    res.status(200).json({ message: 'All notifications marked as read' });
});

module.exports = {
    createNotification,
    getNotifications,
    getUnreadCount,
    markAsRead,
    markAllAsRead,
};
