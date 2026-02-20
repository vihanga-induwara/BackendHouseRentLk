const asyncHandler = require('express-async-handler');
const SavedSearch = require('../models/SavedSearch');

// @desc    Create a saved search
// @route   POST /api/saved-searches
// @access  Private
const createSavedSearch = asyncHandler(async (req, res) => {
    const { name, filters } = req.body;

    if (!name || !filters) {
        res.status(400);
        throw new Error('Please provide a name and search filters');
    }

    const savedSearch = await SavedSearch.create({
        user: req.user.id,
        name,
        filters
    });

    res.status(201).json(savedSearch);
});

// @desc    Get all saved searches for user
// @route   GET /api/saved-searches
// @access  Private
const getMySavedSearches = asyncHandler(async (req, res) => {
    const savedSearches = await SavedSearch.find({ user: req.user.id });
    res.json(savedSearches);
});

// @desc    Delete a saved search
// @route   DELETE /api/saved-searches/:id
// @access  Private
const deleteSavedSearch = asyncHandler(async (req, res) => {
    const savedSearch = await SavedSearch.findById(req.params.id);

    if (!savedSearch) {
        res.status(404);
        throw new Error('Saved search not found');
    }

    if (savedSearch.user.toString() !== req.user.id) {
        res.status(401);
        throw new Error('User not authorized');
    }

    await savedSearch.deleteOne();
    res.json({ message: 'Saved search removed' });
});

module.exports = {
    createSavedSearch,
    getMySavedSearches,
    deleteSavedSearch
};
