function resetFormFields() {
	// Reset all select fields to their first option
	$("#id_code").val('');
	$("#id_destination").val('');
	$("#id_type").val('');
	$("#id_subunit").val('');
	$("#id_subcode").val('');
	$("#id_subdestination").val('');
	$("#id_subtype").val('');
	
	// Hide all optional fields
	hideOptional();

	// Update available order types based on selected unit
	updateOrderTypes();
	updateConversionTypes();
}

function updateOrderTypes() {
	var $unit = $("#id_unit option:selected");
	var $code = $("#id_code");
	
	// Reset order type dropdown
	$code.find('option').show();
	
	if ($unit.length) {
		var unitText = $unit.text();
		// Extract unit type from the text (e.g. "Army in BOL - Bologna")
		var unitType = unitText.split(' in ')[0];
		
		// If unit is a Garrison, only allow Hold, Support and Convert
		if (unitType === 'Garrison') {
			$code.find('option').hide();
			$code.find('option[value="H"]').show(); // Hold
			$code.find('option[value="S"]').show(); // Support
			$code.find('option[value="="]').show(); // Convert
			
			// Reset to empty if current selection is not allowed
			if (!['H','S','='].includes($code.val())) {
				$code.val('');
			}
		}
		// Hide convoy option if not a fleet
		else if (unitType !== 'Fleet') {
			$code.find('option[value="C"]').hide();
			if ($code.val() === 'C') {
				$code.val('');
			}
		}

		// Get area info to determine if Besiege should be available
		var unit_id = $("#id_unit").val();
		$.getJSON(game_url + '/get_area_info/', {
			unit_id: unit_id
		}, function(data) {
			// Hide Besiege option by default
			$code.find('option[value="B"]').hide();
			
			// Only show Besiege if:
			// 1. Area has a fortified city
			// 2. For fleets, city must be a port
			if (data.has_city && data.is_fortified && 
				(unitType === 'Army' || (unitType === 'Fleet' && data.has_port))) {
				$code.find('option[value="B"]').show();
			}
			
			// If Besiege was selected but is now hidden, reset selection
			if (!$code.find('option[value="B"]:visible').length && $code.val() === 'B') {
				$code.val('');
			}
		});
	}
}

function updateConversionTypes() {
	var unit = $("#id_unit").val();
	var code = $("#id_code").val();
	
	if (unit && code === '=') {
		$.getJSON('/machiavelli/game/' + game_slug + '/get_valid_destinations/', {
			unit_id: unit,
			order_type: code
		}, function(data) {
			var $type = $("#id_type");
			$type.empty();
			$type.append($('<option>').val('').text('---'));
			
			if (data.destinations && data.destinations.length > 0) {
				var validTypes = data.destinations[0].valid_types;
				if (validTypes && validTypes.length > 0) {
					$.each(validTypes, function(i, type) {
						var text = '';
						switch(type) {
							case 'A':
								text = 'Army';
								break;
							case 'F':
								text = 'Fleet';
								break;
							case 'G':
								text = 'Garrison';
								break;
						}
						$type.append($('<option>').val(type).text(text));
					});
					$type.parent().fadeIn('slow');
				} else {
					// No valid conversion types available
					$type.append($('<option>').val('').text('No valid conversions available'));
					$type.prop('disabled', true);
					$type.parent().fadeIn('slow');
				}
			} else {
				// No destinations available
				$type.append($('<option>').val('').text('No valid conversions available'));
				$type.prop('disabled', true);
				$type.parent().fadeIn('slow');
			}
		}).fail(function(jqXHR, textStatus, errorThrown) {
			console.error("Failed to get valid destinations:", textStatus, errorThrown);
			console.error("Response:", jqXHR.responseText);
			var $type = $("#id_type");
			$type.empty();
			$type.append($('<option>').val('').text('Error loading conversion types'));
			$type.prop('disabled', true);
			$type.parent().fadeIn('slow');
		});
	}
}

function toggle_params() {
	var code = $("#id_code").val();
	var unit = $("#id_unit").val();
	// Extract unit type from the text (e.g. "Army in BOL - Bologna")
	var unitText = $("#id_unit option:selected").text();
	var unitType = unitText.split(' in ')[0];

	// Hide all optional fields first
	$("#id_destination").parent().hide();
	$("#id_type").parent().hide();
	$("#id_subunit").parent().hide();
	$("#id_subcode").parent().hide();
	$("#id_subdestination").parent().hide();
	$("#id_subtype").parent().hide();

	// Update destinations based on selected unit and order type
	if (unit) {
		$.getJSON('/machiavelli/game/' + game_slug + '/get_valid_destinations/', {
			unit_id: unit,
			order_type: code
		}, function(data) {
			var $dest = $("#id_destination");
			$dest.empty();
			$dest.append($('<option>').val('').text('---'));
			$.each(data.destinations, function(i, item) {
				var text = item.code + ' - ' + item.name;
				if (item.convoy_only) {
					text += ' (via convoy)';
				}
				$dest.append($('<option>').val(item.id).text(text));
			});
		});
	}

	switch (code) {
		case 'H':
		case 'B':
			break;
		case '-':
			$("#id_destination").parent().fadeIn('slow');
			break;
		case '=':
			$("#id_type").parent().fadeIn('slow');
			updateConversionTypes();
			break;
		case 'C':
			// Set subcode to advance (move) for convoy orders
			$("#id_subcode").val('-');
			
			// Show required fields for convoy
			$("#id_subunit").parent().fadeIn('slow');
			$("#id_subcode").parent().fadeIn('slow');
			$("#id_subdestination").parent().fadeIn('slow');
			
			// Disable changing the subcode for convoy orders
			$("#id_subcode option").each(function() {
				if ($(this).val() !== '-') {
					$(this).hide();
				} else {
					$(this).show();
				}
			});

			// Get valid units that can be convoyed
			var unit = $("#id_unit").val();
			console.log("Getting convoyable units for unit:", unit);
			$.getJSON(game_url + '/get_supportable_units/', {
				unit_id: unit,
				for_convoy: true
			}, function(data) {
				console.log("Received convoyable units data:", data);
				if (data && data.units) {
					var $subunit = $("#id_subunit");
					$subunit.empty();
					$subunit.append($('<option>').val('').text('---'));
					$.each(data.units, function(i, item) {
						console.log("Processing unit:", item);
						if (item && item.id && item.description) {
							$subunit.append($('<option>').val(item.id).text(item.description));
						}
					});
					console.log("Final subunit options:", $subunit.html());
				} else {
					console.warn("No valid units data received");
				}
			}).fail(function(jqXHR, textStatus, errorThrown) {
				console.error("Failed to get convoyable units:", textStatus, errorThrown);
				console.error("Response:", jqXHR.responseText);
			});
			break;
		case 'S':
			// Show subunit and subcode fields for support orders
			$("#id_subunit").parent().fadeIn('slow');
			$("#id_subcode").parent().fadeIn('slow');
			
			// For support orders, only show Hold and Advance options
			var $subcode = $("#id_subcode");
			$subcode.find('option').hide();
			$subcode.find('option[value="H"]').show(); // Hold
			$subcode.find('option[value="-"]').show(); // Advance
			if ($subcode.val() && !['H','-'].includes($subcode.val())) {
				$subcode.val('');
			}

			var unit = $("#id_unit").val();
			console.log("Getting supportable units for unit:", unit);
			// Get valid supportable units from backend
			$.getJSON(game_url + '/get_supportable_units/', {
				unit_id: unit,
				for_convoy: false
			}, function(data) {
				console.log("Received supportable units data:", data);
				if (data && data.units) {
					var $subunit = $("#id_subunit");
					$subunit.empty();
					$subunit.append($('<option>').val('').text('---'));
					$.each(data.units, function(i, item) {
						console.log("Processing unit:", item);
						if (item && item.id && item.description) {
							$subunit.append($('<option>').val(item.id).text(item.description));
						}
					});
					console.log("Final subunit options:", $subunit.html());
				} else {
					console.warn("No valid units data received");
				}
			}).fail(function(jqXHR, textStatus, errorThrown) {
				console.error("Failed to get supportable units:", textStatus, errorThrown);
				console.error("Response:", jqXHR.responseText);
			});

			toggle_subparams();
			break;
	}
}

function toggle_subparams() {
	var code = $("#id_subcode").val();
	var unit = $("#id_unit").val();
	var subunit = $("#id_subunit").val();
	var mainCode = $("#id_code").val();
	// Extract unit type from the text (e.g. "Army in BOL - Bologna")
	var unitText = $("#id_unit option:selected").text();
	var unitType = unitText.split(' in ')[0];

	// Hide sub-destination and sub-type by default
	$("#id_subdestination").parent().hide();
	$("#id_subtype").parent().hide();

	// Update sub-destinations if supporting a move
	if (code === '-' && unit && subunit && mainCode === 'S') {
		console.log("Getting support destinations for unit:", unit, "supporting unit:", subunit);
		
		// Get the subunit type from the selected option text
		var subunitText = $("#id_subunit option:selected").text().split(' ')[0];
		console.log("Subunit type:", subunitText);
		
		// Get valid support destinations from backend
		$.getJSON(game_url + '/get_valid_support_destinations/', {
			unit_id: unit,
			supported_unit_id: subunit
		}, function(data) {
			console.log("Got support destinations response:", data);
			if (data && Array.isArray(data.destinations)) {
				var $subdest = $("#id_subdestination");
				$subdest.empty();
				$subdest.append($('<option>').val('').text('---'));
				$.each(data.destinations, function(i, item) {
					console.log("Adding destination:", item);
					var text = item.code + ' - ' + item.name;
					$subdest.append($('<option>').val(item.id).text(text));
				});
				if (data.destinations.length > 0) {
					$("#id_subdestination").parent().fadeIn('slow');
				} else {
					console.warn("No valid destinations received");
				}
			} else {
				console.error("Invalid destinations data received:", data);
			}
		}).fail(function(jqXHR, textStatus, errorThrown) {
			console.error("Failed to get support destinations:", textStatus, errorThrown);
			console.error("Response:", jqXHR.responseText);
		});
	}

	// For convoy orders, show subdestination and get valid coastal destinations
	if (mainCode === 'C' && unit && subunit) {
		$("#id_subcode").val('-');
		console.log("Getting convoy destinations for unit:", unit, "convoying unit:", subunit);
		$.getJSON(game_url + '/get_valid_support_destinations/', {
			unit_id: unit,
			supported_unit_id: subunit,
			for_convoy: true
		}, function(data) {
			console.log("Got convoy destinations response:", data);
			if (data && Array.isArray(data.destinations)) {
				var $subdest = $("#id_subdestination");
				$subdest.empty();
				$subdest.append($('<option>').val('').text('---'));
				$.each(data.destinations, function(i, item) {
					console.log("Adding destination:", item);
					var text = item.code + ' - ' + item.name;
					$subdest.append($('<option>').val(item.id).text(text));
				});
				if (data.destinations.length > 0) {
					$("#id_subdestination").parent().fadeIn('slow');
				} else {
					console.warn("No valid destinations received");
				}
			} else {
				console.error("Invalid destinations data received:", data);
			}
		}).fail(function(jqXHR, textStatus, errorThrown) {
			console.error("Failed to get convoy destinations:", textStatus, errorThrown);
			console.error("Response:", jqXHR.responseText);
		});
	}
	// For support orders, show based on subcode
	else if (mainCode === 'S') {
		switch (code) {
			case 'H':
				break;
			case '-':
				$("#id_subdestination").parent().fadeIn('slow');
				break;
		}
	}
}

function hideOptional() {
	$("#id_destination").parent().hide();
	$("#id_type").parent().hide();
	$("#id_subunit").parent().hide();
	$("#id_subcode").parent().hide();
	$("#id_subdestination").parent().hide();
	$("#id_subtype").parent().hide();
}

function addChangeHandlers() {
	$("#id_unit").change(function() {
		resetFormFields();
		updateOrderTypes();
		updateConversionTypes();
	});
	$("#id_code").change(function() {
		toggle_params();
	});
	$("#id_subcode").change(function() {
		toggle_subparams();
	});
	$("#id_subunit").change(function() {
		toggle_subparams(); 
	});
}

function deleteOrder(pk) {
	$.getJSON(game_url + "/delete_order/" + pk, orderDeleted)
}

function orderDeleted(data) {
	var e_msg = '';

	if (data) {
		if (eval(data.bad)) {
			$('#so_emsg').text("Error: Order could not be deleted. ").fadeIn("slow");
		} else {
			$("#order_" + data.order_id).fadeOut('slow');
		}
	} else {
		$('#so_emsg').text("Ajax error: no data received. ").fadeIn("slow");
	}
}

function processOrderJson(data) {
	var e_msg = '';
	if (data) {
		if (eval(data.bad)) {
			errors = eval(data.errs)
			for (field in errors) {
				if (field == '__all__') {
					$("#emsg").html(errors[field]);
					$("#emsg").fadeIn('slow');
				} else {
					$('#id_' + field).parent().before(errors[field]);
				}
			}
		} else {
			var new_li = '<li id="order_' + data.pk + '">';
			new_li += data.new_order;
			new_li += ' (<a href="' + game_url + '/delete_order/';
			new_li += data.pk;
			new_li += '" class="delete_order">';
			new_li += delete_text;
			new_li += '</a>)</li>';
			$(new_li).hide().appendTo("#sent_orders").fadeIn("slow");
			addClickHandlers();
			
			// Reset the form
			$("#id_unit").val('');
			resetFormFields();
		}
	} else {
		$('#emsg').text("Ajax error: no data received. ").fadeIn("slow");
	}
}

function prepareForm() {
	var options = {
		url: game_url,
		dataType: 'json',
		success: processOrderJson,
		beforeSubmit: beforeForm
	};
	$('#order_form').ajaxForm(options);

	// Ensure form submits correctly by setting certain values when needed
	$('#order_form').submit(function() {
		// For convoy orders, ensure subcode is set to advance
		if ($("#id_code").val() === 'C') {
			$("#id_subcode").val('-');
		}
		return true;
	});
}

function beforeForm(formData, jqForm, options) {
	$('.errorlist').remove();
	$('#emsg').html('&nbsp;').hide();
}

function addClickHandlers() {
	$('a.delete_order').click( function(e) {
		e.preventDefault();
		pk = $(this).parent().attr("id").split('_')[1];
		deleteOrder(pk);
	});
}

$(document).ready(function() {
	hideOptional();
	prepareForm();
	addClickHandlers();
	addChangeHandlers();
	});
