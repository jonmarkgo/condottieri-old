/*
order_form.js - Handles dynamic interactions for the Machiavelli order form.

Dependencies: jQuery, jQuery UI (optional, for effects), jquery.form.js (for AJAX submission)
*/

// Ensure global AJAX settings handle CSRF token
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
var csrftoken = getCookie('csrftoken');

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});


// Helper function to populate dropdowns
function populate_dropdown(dropdown, data, value_key, text_key, add_blank) {
    dropdown.empty(); // Clear existing options
    if (add_blank) {
        dropdown.append($('<option>', { value: '', text: '---' }));
    }
    $.each(data, function(index, item) {
        dropdown.append($('<option>', {
            value: item[value_key],
            text: item[text_key]
        }));
    });
    dropdown.trigger('change'); // Trigger change event for potential dependencies
}

// Helper function to clear dropdowns
function clear_dropdown(dropdown, add_blank) {
    dropdown.empty();
    if (add_blank) {
        dropdown.append($('<option>', { value: '', text: '---' }));
    }
    // Disable dropdown if it has no real options? Maybe not necessary.
    // dropdown.prop('disabled', dropdown.children('option').length <= (add_blank ? 1 : 0));
}

// Helper function to show/hide form rows based on visibility flag
function toggle_field_row(field_id, show) {
    // Assumes fields are wrapped in <p> or <tr> elements by Django form rendering (e.g., as_p)
    // Adjust selector if your form structure is different (e.g., 'div', 'li')
    var field_element = $('#' + field_id);
    var wrapper = field_element.closest('p'); // Or 'tr', 'div.form-group', etc.
    if (wrapper.length === 0) {
        // Fallback if direct parent isn't the row wrapper
        wrapper = field_element.parent();
    }
    if (show) {
        wrapper.show();
    } else {
        wrapper.hide();
        // Optionally clear the field value when hiding
        if (field_element.is('select')) {
            field_element.val('');
        } else if (field_element.is(':text, :hidden')) {
             field_element.val('');
        } // Add other types if needed
    }
}

// Function to control field visibility based on selected order code
function toggle_fields() {
    var code = $('#id_code').val();
    var subcode = $('#id_subcode').val(); // Needed for support variations

    // Hide all optional fields initially
    toggle_field_row('id_destination', false);
    toggle_field_row('id_destination_coast', false);
    toggle_field_row('id_type', false);
    toggle_field_row('id_subunit', false);
    toggle_field_row('id_subcode', false);
    toggle_field_row('id_subdestination', false);
    toggle_field_row('id_subdestination_coast', false);
    toggle_field_row('id_subtype', false);

    // Show fields based on code
    if (code === '-') { // Advance
        toggle_field_row('id_destination', true);
        // Coast visibility depends on selected destination, handled by check_coast()
    } else if (code === '=') { // Conversion
        toggle_field_row('id_type', true);
    } else if (code === 'C') { // Convoy
        toggle_field_row('id_subunit', true);
        toggle_field_row('id_subdestination', true);
        // Coast visibility depends on selected subdestination, handled by check_coast()
    } else if (code === 'S') { // Support
        toggle_field_row('id_subunit', true);
        toggle_field_row('id_subcode', true);
        if (subcode === '-') { // Support Move
            toggle_field_row('id_subdestination', true);
            // Coast visibility depends on selected subdestination, handled by check_coast()
        } else if (subcode === '=') { // Support Conversion (If ever allowed)
            toggle_field_row('id_subtype', true);
        }
        // Support Hold (subcode 'H' or empty) needs no further fields beyond subunit/subcode
    }
    // H, B, L, 0 need no extra fields beyond unit/code
}

// Function to fetch valid destinations for Advance or Conversion types
function fetch_destinations() {
    var unit_id = $('#id_unit').val();
    var code = $('#id_code').val();
    var dest_dropdown = $('#id_destination');
    var type_dropdown = $('#id_type');

    clear_dropdown(dest_dropdown, true);
    clear_dropdown(type_dropdown, true);
    toggle_field_row('id_destination_coast', false); // Hide coast initially

    if (!unit_id || (code !== '-' && code !== '=')) {
        return; // No unit selected or code doesn't need destinations/types
    }

    console.log("Fetching destinations/types for unit:", unit_id, "code:", code);
    $.ajax({
        url: ajax_get_valid_destinations_url, // Use global URL variable
        data: { 'unit_id': unit_id, 'order_code': code },
        dataType: 'json',
        success: function(data) {
            console.log("Destinations/Types response:", data);
            if (code === '-') {
                populate_dropdown(dest_dropdown, data.destinations, 'id', 'name', true);
            } else if (code === '=') {
                // Conversion uses the 'type' dropdown
                if (data.destinations.length > 0 && data.destinations[0].valid_types) {
                    var valid_types_options = data.destinations[0].valid_types.map(function(t) {
                        // Assuming UNIT_TYPES is available or map manually
                        var type_name = t; // Default
                        if (t === 'A') type_name = 'Army';
                        else if (t === 'F') type_name = 'Fleet';
                        else if (t === 'G') type_name = 'Garrison';
                        return { value: t, text: type_name };
                    });
                    populate_dropdown(type_dropdown, valid_types_options, 'value', 'text', true);
                }
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error("Error fetching destinations/types:", textStatus, errorThrown);
            // Optionally display an error message to the user
        }
    });
}

// Function to fetch valid target units for Support or Convoy
function fetch_subunits() {
    var unit_id = $('#id_unit').val(); // The unit giving the order
    var code = $('#id_code').val();
    var subunit_dropdown = $('#id_subunit');

    clear_dropdown(subunit_dropdown, true);
    clear_dropdown($('#id_subdestination'), true); // Clear dependent fields
    clear_dropdown($('#id_subtype'), true);
    toggle_field_row('id_subdestination_coast', false);

    if (!unit_id || (code !== 'S' && code !== 'C')) {
        return; // No unit selected or code doesn't need subunit
    }

    console.log("Fetching subunits for unit:", unit_id, "code:", code);
    var ajax_url = (code === 'S') ? ajax_get_supportable_units_url : ajax_get_supportable_units_url; // Use same URL for now, view logic differentiates? Or need separate URLs? Let's assume get_supportable_units handles both based on unit type.
    // If convoy needs specific filtering (only armies), the view should handle it.

    $.ajax({
        url: ajax_url, // Use appropriate URL variable
        // Need to pass target_area_id for support? This makes it complex.
        // Let's simplify: get_supportable_units returns *all* potentially supportable units nearby.
        // The user selecting the subunit implies the target area.
        data: { 'unit_id': unit_id }, // Pass the supporting/convoying unit
        dataType: 'json',
        success: function(data) {
            console.log("Subunits response:", data);
            populate_dropdown(subunit_dropdown, data.units, 'id', 'description', true);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error("Error fetching subunits:", textStatus, errorThrown);
        }
    });
}

// Function to fetch valid destinations for Support Move or Convoy
function fetch_subdestinations() {
    var unit_id = $('#id_unit').val(); // The supporting/convoying unit
    var subunit_id = $('#id_subunit').val(); // The supported/convoyed unit
    var code = $('#id_code').val();
    var subcode = $('#id_subcode').val();
    var subdest_dropdown = $('#id_subdestination');

    clear_dropdown(subdest_dropdown, true);
    toggle_field_row('id_subdestination_coast', false);

    if (!unit_id || !subunit_id || (code !== 'C' && !(code === 'S' && subcode === '-'))) {
        return; // Conditions not met
    }

    console.log("Fetching sub-destinations for unit:", unit_id, "subunit:", subunit_id, "code:", code, "subcode:", subcode);
    var ajax_url = '';
    var ajax_data = {};

    if (code === 'C') {
        // For convoy, find where the *convoyed unit* (subunit) can move via convoy
        // Use get_valid_destinations for the subunit, filtering for convoy_only? Or rely on view?
        // Let's use get_valid_destinations for the *subunit* and assume JS/user filters later.
        ajax_url = ajax_get_valid_destinations_url;
        ajax_data = { 'unit_id': subunit_id, 'order_code': '-' }; // Find where subunit could normally advance
    } else if (code === 'S' && subcode === '-') {
        // For support move, find where the *supporter* (unit) can support a move *into*
        ajax_url = ajax_get_valid_support_destinations_url;
        ajax_data = { 'unit_id': unit_id }; // Pass the supporting unit
    } else {
        return; // Should not happen
    }

    $.ajax({
        url: ajax_url,
        data: ajax_data,
        dataType: 'json',
        success: function(data) {
            console.log("Sub-destinations response:", data);
            if (code === 'C') {
                // Filter destinations for convoy: must be coastal and not adjacent to subunit start?
                // Simplification: Show all potential advance destinations for subunit. User/validation must ensure convoy path.
                 populate_dropdown(subdest_dropdown, data.destinations, 'id', 'name', true);
            } else { // Support Move
                 populate_dropdown(subdest_dropdown, data.destinations, 'id', 'name', true);
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error("Error fetching sub-destinations:", textStatus, errorThrown);
        }
    });
}


// Function to check if coast selection is needed and populate/show/hide
function check_coast(area_dropdown_selector, coast_dropdown_selector) {
    var area_id = $(area_dropdown_selector).val();
    var coast_dropdown = $(coast_dropdown_selector);
    var code = $('#id_code').val();
    var subcode = $('#id_subcode').val();
    var unit_type = ''; // Determine relevant unit type (fleet or convoyed army)

    // Determine if coast is relevant for the current order
    var coast_is_relevant = false;
    if (area_id) {
        if (area_dropdown_selector === '#id_destination') {
            // Destination coast relevant for Fleet Advance or Army Convoy
            var main_unit_type = $('#id_unit option:selected').text().substring(0, 1); // Get type (A/F/G) from unit dropdown text
            if ((code === '-' && main_unit_type === 'F') || code === 'C') {
                coast_is_relevant = true;
            }
        } else if (area_dropdown_selector === '#id_subdestination') {
            // Subdestination coast relevant for Convoy or Support Fleet Move
             if (code === 'C') {
                 coast_is_relevant = true;
             } else if (code === 'S' && subcode === '-') {
                 var subunit_text = $('#id_subunit option:selected').text();
                 if (subunit_text && subunit_text.substring(0, 1) === 'F') { // Check if supporting a Fleet
                     coast_is_relevant = true;
                 }
             }
        }
    }

    // Hide coast dropdown if area not selected or coast not relevant for the order
    if (!area_id || !coast_is_relevant) {
        toggle_field_row(coast_dropdown.attr('id'), false);
        clear_dropdown(coast_dropdown, true); // Clear options
        return;
    }

    console.log("Checking coast for area:", area_id, "for dropdown:", coast_dropdown_selector);
    // Fetch area info to get coasts
    $.ajax({
        url: ajax_get_area_info_url, // Use global URL variable
        data: { 'area_id': area_id },
        dataType: 'json',
        success: function(data) {
            console.log("Area info response:", data);
            if (data.coasts && data.coasts.length > 0) {
                // Area has coasts (likely multi-coast) - show and populate dropdown
                var coast_options = data.coasts.map(function(c) {
                    // Assuming coast codes are 'nc', 'sc', etc. and display names are 'NC', 'SC'
                    return { value: c.toLowerCase(), text: c.toUpperCase() };
                });
                populate_dropdown(coast_dropdown, coast_options, 'value', 'text', true);
                toggle_field_row(coast_dropdown.attr('id'), true); // Show the row
            } else {
                // Area has no coasts defined (single coast or non-coastal) - hide dropdown
                toggle_field_row(coast_dropdown.attr('id'), false);
                clear_dropdown(coast_dropdown, true);
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error("Error fetching area info:", textStatus, errorThrown);
            toggle_field_row(coast_dropdown.attr('id'), false); // Hide on error
            clear_dropdown(coast_dropdown, true);
        }
    });
}


// --- Document Ready ---
$(document).ready(function() {

    // --- Initial Setup ---
    toggle_fields(); // Set initial field visibility

    // --- Event Handlers ---
    $('#id_code').change(function() {
        toggle_fields();
        // Fetch data needed for the new code
        var code = $(this).val();
        if (code === '-' || code === '=') {
            fetch_destinations();
        } else if (code === 'S' || code === 'C') {
            fetch_subunits();
        }
        // Clear potentially invalid selections in dependent fields
        clear_dropdown($('#id_destination'), true);
        clear_dropdown($('#id_type'), true);
        clear_dropdown($('#id_subunit'), true);
        clear_dropdown($('#id_subcode'), true);
        clear_dropdown($('#id_subdestination'), true);
        clear_dropdown($('#id_subtype'), true);
        toggle_field_row('id_destination_coast', false);
        toggle_field_row('id_subdestination_coast', false);
    });

    $('#id_unit').change(function() {
        // Re-fetch data based on the new unit, if code requires it
        var code = $('#id_code').val();
         if (code === '-' || code === '=') {
            fetch_destinations();
        } else if (code === 'S' || code === 'C') {
            fetch_subunits(); // Re-fetch subunits based on new supporter/convoyer
        }
        // Clear potentially invalid selections
        clear_dropdown($('#id_destination'), true);
        clear_dropdown($('#id_type'), true);
        clear_dropdown($('#id_subunit'), true);
        clear_dropdown($('#id_subcode'), true);
        clear_dropdown($('#id_subdestination'), true);
        clear_dropdown($('#id_subtype'), true);
        toggle_field_row('id_destination_coast', false);
        toggle_field_row('id_subdestination_coast', false);
    });

    $('#id_destination').change(function() {
        check_coast('#id_destination', '#id_destination_coast');
    });

    $('#id_subunit').change(function() {
        // If supporting, fetch possible sub-destinations based on new subunit?
        // This is complex. Let's fetch subdestinations based on supporter only for now.
        var code = $('#id_code').val();
        var subcode = $('#id_subcode').val();
         if (code === 'S' && subcode === '-') {
             fetch_subdestinations(); // Re-fetch based on supporter, user must ensure it matches subunit move
         } else if (code === 'C') {
             fetch_subdestinations(); // Re-fetch based on convoyed unit
         }
         // Clear potentially invalid sub-destination coast
         clear_dropdown($('#id_subdestination'), true);
         toggle_field_row('id_subdestination_coast', false);
    });

     $('#id_subcode').change(function() {
         toggle_fields(); // Show/hide subdest/subtype based on subcode
         var code = $('#id_code').val();
         var subcode = $(this).val();
         if (code === 'S' && subcode === '-') {
             fetch_subdestinations(); // Fetch destinations for support move
         }
         // Clear potentially invalid sub-destination/subtype/coast
         clear_dropdown($('#id_subdestination'), true);
         clear_dropdown($('#id_subtype'), true);
         toggle_field_row('id_subdestination_coast', false);
     });

    $('#id_subdestination').change(function() {
        check_coast('#id_subdestination', '#id_subdestination_coast');
    });


    // --- AJAX Form Submission ---
    var options = {
        target:     '#sent_orders', // Target is the UL element
        url:        $('#order_form').attr('action'), // Get URL from form action
        type:       'post',
        dataType:   'json', // Expect JSON response
        beforeSubmit: function(formData, jqForm, options) {
            // Clear previous errors
            $('#emsg').hide().empty();
            // Can add validation here if needed
            console.log("Submitting order:", formData);
            return true; // Proceed with submission
        },
        success: function(response, statusText, xhr, $form) {
            console.log("Order submission response:", response);
            if (response.bad === 'true') {
                // Display errors
                var error_html = '<ul>';
                $.each(response.errs, function(field, errors) {
                    error_html += '<li>' + (field !== '__all__' ? field + ': ' : '') + errors.join(', ') + '</li>';
                });
                error_html += '</ul>';
                $('#emsg').html(error_html).show();
            } else {
                // Success - add new order to list and reset form
                var new_li_id = 'order_' + response.pk;
                // Add delete link dynamically
                var delete_url = ajax_delete_order_url_base + response.pk + '/'; // Construct delete URL
                var new_li_html = '<li id="' + new_li_id + '">' + response.new_order +
                                  ' (<a href="' + delete_url + '" class="delete_order">' + delete_text + '</a>)' +
                                  '</li>';

                // Remove placeholder if present
                $('#sent_orders li:contains("No orders sent yet.")').remove();
                // Prepend or append the new order
                $('#sent_orders').append(new_li_html);
                // Reset the form fields
                $form.resetForm();
                // Re-initialize fields (clear dropdowns, toggle visibility)
                toggle_fields();
                clear_dropdown($('#id_destination'), true);
                clear_dropdown($('#id_type'), true);
                clear_dropdown($('#id_subunit'), true);
                clear_dropdown($('#id_subcode'), true);
                clear_dropdown($('#id_subdestination'), true);
                clear_dropdown($('#id_subtype'), true);
                toggle_field_row('id_destination_coast', false);
                toggle_field_row('id_subdestination_coast', false);
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
             console.error("Error submitting order:", textStatus, errorThrown);
             $('#emsg').html('An unexpected error occurred. Please try again.').show();
        }
    };

    // Bind the form submission
    $('#order_form').ajaxForm(options);


    // --- Delete Order Link ---
    // Use event delegation for dynamically added links
    $('#sent_orders').on('click', 'a.delete_order', function(e) {
        e.preventDefault(); // Prevent default link navigation
        var delete_url = $(this).attr('href');
        var li_element = $(this).closest('li');
        var order_id = li_element.attr('id').split('_')[1];

        console.log("Deleting order:", order_id, "URL:", delete_url);

        $.ajax({
            url: delete_url,
            type: 'POST', // Use POST for deletion
            dataType: 'json',
            // No data needed if using URL routing for ID
            success: function(response) {
                console.log("Delete response:", response);
                if (response.bad === 'false' && response.order_id == order_id) {
                    // Remove the list item on success
                    li_element.fadeOut(300, function() { $(this).remove(); });
                     // Optionally add placeholder back if list becomes empty
                     if ($('#sent_orders li').length === 0) {
                         $('#sent_orders').html('<li>No orders sent yet.</li>');
                     }
                } else {
                    // Display error message
                    var error_msg = response.error || 'Failed to delete order.';
                    $('#so_emsg').text(error_msg).show().delay(3000).fadeOut(); // Show error near list
                }
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.error("Error deleting order:", textStatus, errorThrown);
                 $('#so_emsg').text('An unexpected error occurred while deleting.').show().delay(3000).fadeOut();
            }
        });
    });

}); // End document ready