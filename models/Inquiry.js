const mongoose = require('mongoose');

const replySchema = new mongoose.Schema({
    sender: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true,
    },
    message: {
        type: String,
        required: true,
        maxlength: 1000,
    },
    createdAt: {
        type: Date,
        default: Date.now,
    },
});

const inquirySchema = new mongoose.Schema(
    {
        listing: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'Listing',
            required: true,
        },
        sender: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'User',
            required: true,
        },
        owner: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'User',
            required: true,
        },
        message: {
            type: String,
            required: true,
            maxlength: 1000,
        },
        replies: [replySchema],
        status: {
            type: String,
            enum: ['new', 'read', 'replied', 'closed'],
            default: 'new',
        },
    },
    { timestamps: true }
);

inquirySchema.index({ owner: 1, createdAt: -1 });
inquirySchema.index({ sender: 1, createdAt: -1 });

module.exports = mongoose.model('Inquiry', inquirySchema);
