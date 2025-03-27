/**
 * order_form.js
 *
 * Handles dynamic interactions for the Machiavelli order form,
 * including showing/hiding/populating coast selection fields.
 */

// Ensure URLs are defined in the template scope before this script runs. Example:
// <script>
//     var ajax_get_area_info_url = "{% url 'get-area-info' game.slug %}";
//     // Define other needed URLs...
// </script>

$(document).ready(function() {
    // --- Configuration ---
    var AREA_INFO_URL = typeof ajax_get_area_info_url !== 'undefined' ? ajax_get_area_info_url : '';
    if (!AREA_INFO_URL) {
        console.error("Machiavelli order_form.js: ajax_get_area_info_url is not defined. Coast fields will not work.");
    }
    // Add other AJAX URLs if needed by other dynamic parts of the form

    // --- DOM Element Selectors ---
    var $form = $('#order_form'); // The main form
    var $unitSelect = $form.find('#id_unit');
    var $orderCodeSelect = $form.find('#id_code');
    var $destinationSelect = $form.find('#id_destination');
    var $destinationCoastSelect = $form.find('#id_destination_coast');
    var $destinationCoastWrapper = $destinationCoastSelect.closest('p, div'); // Adjust selector if needed

    var $typeSelect = $form.find('#id_type'); // Conversion type

    var $subunitSelect = $form.find('#id_subunit');
    var $subcodeSelect = $form.find('#id_subcode');
    var $subdestinationSelect = $form.find('#id_subdestination');
    var $subdestinationCoastSelect = $form.find('#id_subdestination_coast');
    var $subdestinationCoastWrapper = $subdestinationCoastSelect.closest('p, div'); // Adjust selector if needed

    var $subtypeSelect = $form.find('#id_subtype'); // Support conversion type

    // --- Helper Functions ---

    // Function to get Unit Type from select option text (e.g., "F in lon/nc")
    function getUnitTypeFromOption($option) {
        if (!$option || !$option.text()) {
            return null;
        }
        var text = $option.text().trim();
        // Match A, F, or G at the beginning of the string
        var match = text.match(/^[AFG]/);
        if (match) {
            return match[0];
        }
        console.warn("Could not determine unit type from option text:", text);
        return null;
    }

    // Function to populate a coast select dropdown
    function populateCoastSelect($select, coasts) {
        var currentVal = $select.val(); // Preserve selection if possible
        $select.empty(); // Clear existing options
        $select.append($('<option>').val('').text('---')); // Add default blank option
        var optionsAdded = false;
        if (coasts && Array.isArray(coasts) && coasts.length > 0) {
            $.each(coasts, function(index, coastCode) {
                if (coastCode) { // Ensure coast code is not empty/null
                    var upperCode = coastCode.toUpperCase();
                    var $option = $('<option>').val(coastCode).text(upperCode);
                    if (coastCode === currentVal) {
                        $option.prop('selected', true); // Restore selection
                    }
                    $select.append($option);
                    optionsAdded = true;
                }
            });
        }
        // Ensure selection is reset if previous value is no longer valid
        if ($select.val() === null || $select.val() === '') {
             $select.find('option:first').prop('selected', true);
        }
        return optionsAdded; // Return true if actual coast options were added
    }

    // Main function to update form state, including coast fields
    function updateFormState() {
        // Hide coast fields initially
        $destinationCoastWrapper.hide();
        $subdestinationCoastWrapper.hide();
        // Optional: Clear coast selections when hiding
        // $destinationCoastSelect.val('');
        // $subdestinationCoastSelect.val('');

        // Get current selections
        var unitId = $unitSelect.val();
        var selectedUnitOption = $unitSelect.find('option:selected');
        var unitType = getUnitTypeFromOption(selectedUnitOption);
        var orderCode = $orderCodeSelect.val();
        var destinationId = $destinationSelect.val();
        var subunitId = $subunitSelect.val();
        var subcode = $subcodeSelect.val();
        var subdestinationId = $subdestinationSelect.val();

        // --- Destination Coast Logic ---
        var requireDestinationCoast = false;
        if (unitType === 'F' && orderCode === '-' && destinationId) {
            // Fleet moving requires coast check for destination
            requireDestinationCoast = true;
        }

        if (requireDestinationCoast && AREA_INFO_URL) {
            $.get(AREA_INFO_URL, { area_id: destinationId }, function(data) {
                if (data && data.coasts && data.coasts.length > 0) {
                    // Only show if there are actual coast options
                    if (populateCoastSelect($destinationCoastSelect, data.coasts)) {
                        $destinationCoastWrapper.show();
                    }
                }
                // If no coasts or error, wrapper remains hidden
            }).fail(function() {
                console.error("Failed to get area info for destination: " + destinationId);
            });
        }

        // --- Sub-Destination Coast Logic ---
        var requireSubdestinationCoast = false;
        if (orderCode === 'C' && subdestinationId) {
            // Convoy destination requires coast check
            requireSubdestinationCoast = true;
        } else if (orderCode === 'S' && subcode === '-' && subdestinationId) {
            // Support Move destination requires coast check
            requireSubdestinationCoast = true;
        }

        if (requireSubdestinationCoast && AREA_INFO_URL) {
            $.get(AREA_INFO_URL, { area_id: subdestinationId }, function(data) {
                if (data && data.coasts && data.coasts.length > 0) {
                    // Only show if there are actual coast options
                    if (populateCoastSelect($subdestinationCoastSelect, data.coasts)) {
                        $subdestinationCoastWrapper.show();
                    }
                }
                // If no coasts or error, wrapper remains hidden
            }).fail(function() {
                console.error("Failed to get area info for subdestination: " + subdestinationId);
            });
        }

        // --- Optional: Show/Hide other fields based on orderCode ---
        // (Add logic here if needed to hide/show subunit, destination, type fields etc.)
        // Example:
        // if (orderCode === 'H' || orderCode === 'B' || orderCode === 'L' || orderCode === '0') {
        //     $destinationSelect.closest('p, div').hide();
        //     $subunitSelect.closest('p, div').hide();
        //     // ... hide others ...
        // } else if (orderCode === '-') {
        //     $destinationSelect.closest('p, div').show();
        //     $subunitSelect.closest('p, div').hide();
        //     // ... show/hide others ...
        // } // etc.
    }

    // --- Event Handlers ---
    // Use 'change' event for select dropdowns
    $unitSelect.on('change', updateFormState);
    $orderCodeSelect.on('change', updateFormState);
    $destinationSelect.on('change', updateFormState);
    $subunitSelect.on('change', updateFormState); // May trigger subdest coast check if supporting move
    $subcodeSelect.on('change', updateFormState);
    $subdestinationSelect.on('change', updateFormState);

    // --- Initial Setup ---
    // Ensure wrappers are hidden initially if they contain the selects
    $destinationCoastWrapper.hide();
    $subdestinationCoastWrapper.hide();
    // Run once on page load to set initial visibility based on any pre-filled form data
    updateFormState();

    // --- Optional: AJAX form submission (if used previously) ---
    // $('#order_form').ajaxForm({
    //     dataType: 'json',
    //     beforeSubmit: function(formData, jqForm, options) {
    //         // Add validation or loading indicator
    //     },
    //     success: function(data, statusText, xhr, $form) {
    //         if (data.bad === 'true') {
    //             // Display errors
    //             $('#emsg').html(JSON.stringify(data.errs)).show(); // Simple error display
    //         } else {
    //             // Add new order to list, clear form, update UI
    //             $('#sent_orders').append('<li id="order_' + data.pk + '">' + data.new_order + ' (<a href="' + ajax_delete_order_url_base + data.pk + '/" class="delete_order">Delete</a>)</li>');
    //             $('#emsg').hide();
    //             $form.clearForm(); // Requires form plugin
    //             updateFormState(); // Reset dynamic fields
    //         }
    //     },
    //     error: function() {
    //         $('#emsg').html('An error occurred submitting the order.').show();
    //     }
    // });

    // --- Optional: AJAX order deletion (if used previously) ---
    // $('#sent_orders').on('click', 'a.delete_order', function(e) {
    //     e.preventDefault();
    //     var deleteUrl = $(this).attr('href');
    //     var $listItem = $(this).closest('li');
    //     if (confirm('Are you sure you want to delete this order?')) {
    //         $.post(deleteUrl, { csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val() }, function(data) {
    //             if (data.bad === 'false') {
    //                 $listItem.remove();
    //                 $('#so_emsg').hide();
    //             } else {
    //                 $('#so_emsg').html('Failed to delete order.').show();
    //             }
    //         }, 'json').fail(function() {
    //              $('#so_emsg').html('Error communicating with server.').show();
    //         });
    //     }
    // });


}); // End document ready