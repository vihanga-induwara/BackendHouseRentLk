const express = require('express');
const router = express.Router();
const {
    createSavedSearch,
    getMySavedSearches,
    deleteSavedSearch
} = require('../controllers/savedSearchController');
const { protect } = require('../middleware/authMiddleware');

router.use(protect);

router.route('/')
    .post(createSavedSearch)
    .get(getMySavedSearches);

router.route('/:id')
    .delete(deleteSavedSearch);

module.exports = router;
