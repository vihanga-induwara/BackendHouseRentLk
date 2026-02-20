const express = require('express');
const router = express.Router();
const {
    sendInquiry,
    getReceivedInquiries,
    getSentInquiries,
    getInquiry,
    replyToInquiry,
    closeInquiry,
} = require('../controllers/inquiryController');
const { protect } = require('../middleware/authMiddleware');

router.use(protect);

router.post('/', sendInquiry);
router.get('/received', getReceivedInquiries);
router.get('/sent', getSentInquiries);
router.get('/:id', getInquiry);
router.post('/:id/reply', replyToInquiry);
router.put('/:id/close', closeInquiry);

module.exports = router;
