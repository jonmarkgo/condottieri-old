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
	
	// Hide convoy option if not a fleet
	if ($unit.length && $unit.text().indexOf('Fleet') !== 0) {
		$code.find('option[value="C"]').hide();
		// If convoy was selected, reset it
		if ($code.val() === 'C') {
			$code.val('');
		}
	}
}

function updateConversionTypes() {
	var $unit = $("#id_unit option:selected");
	var $type = $("#id_type");
	
	// Reset conversion type dropdown
	$type.find('option').show();
	
	if ($unit.length) {
		// Get current unit type from text (Army, Fleet, or Garrison)
		var unitText = $unit.text().split(' ')[0];
		// Hide current unit type from conversion options
		$type.find('option').each(function() {
			if ($(this).text() === unitText) {
				$(this).hide();
				// If this type was selected, reset it
				if ($type.val() === $(this).val()) {
					$type.val('');
				}
			}
		});

		// Hide garrison option if area has no city
		$.getJSON(game_url + '/get_area_info/', {
			unit_id: $("#id_unit").val()
		}, function(data) {
			if (!data.has_city) {
				$type.find('option[value="G"]').hide();
				if ($type.val() === 'G') {
					$type.val('');
				}
			}
		});
	}
}

function toggle_params() {
	var code = $("#id_code").val();
	var unit = $("#id_unit").val();

	// Hide all optional fields first
	$("#id_destination").parent().hide();
	$("#id_type").parent().hide();
	$("#id_subunit").parent().hide();
	$("#id_subcode").parent().hide();
	$("#id_subdestination").parent().hide();
	$("#id_subtype").parent().hide();

	// Update destinations based on selected unit and order type
	if (unit) {
		$.getJSON(game_url + '/get_valid_destinations/', {
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
			// For convoy orders, also update subdestination with same options
			if (code === 'C') {
				var $subdest = $("#id_subdestination");
				$subdest.empty();
				$subdest.append($('<option>').val('').text('---'));
				$.each(data.destinations, function(i, item) {
					var text = item.code + ' - ' + item.name;
					$subdest.append($('<option>').val(item.id).text(text));
				});
				
				// Also update available subunits for convoy
				if (data.convoy_units) {
					var $subunit = $("#id_subunit");
					$subunit.empty();
					$subunit.append($('<option>').val('').text('---'));
					$.each(data.convoy_units, function(i, item) {
						$subunit.append($('<option>').val(item.id).text(item.description));
					});
				}
			}
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
			break;
		case 'S':
			// Show all units again for support orders
			$("#id_subunit option").show();
			$("#id_subunit").parent().fadeIn('slow');
			$("#id_subcode").parent().fadeIn('slow');
			// Show all subcode options for support
			$("#id_subcode option").show();
			toggle_subparams();
			break;
	}
}

function toggle_subparams() {
	var code = $("#id_subcode").val();
	var unit = $("#id_unit").val();
	var subunit = $("#id_subunit").val();
	var mainCode = $("#id_code").val();

	// Hide sub-destination and sub-type by default
	$("#id_subdestination").parent().hide();
	$("#id_subtype").parent().hide();

	// Update sub-destinations if supporting a move
	if (code == '-' && unit && subunit) {
		$.getJSON(game_url + '/get_valid_support_destinations/', {
			unit_id: unit,
			supported_unit_id: subunit
		}, function(data) {
			var $subdest = $("#id_subdestination");
			$subdest.empty();
			$subdest.append($('<option>').val('').text('---'));
			$.each(data.destinations, function(i, item) {
				var text = item.code + ' - ' + item.name;
				$subdest.append($('<option>').val(item.id).text(text));
			});
			$("#id_subdestination").parent().fadeIn('slow');
		});
	}

	// For convoy orders, always show subdestination and set subcode to advance
	if (mainCode === 'C') {
		$("#id_subcode").val('-');
		$("#id_subdestination").parent().fadeIn('slow');
	}
	// For support orders, show based on subcode
	else if (mainCode === 'S') {
		switch (code) {
			case 'H':
				break;
			case '-':
				$("#id_subdestination").parent().fadeIn('slow');
				break;
			case '=':
				$("#id_subtype").parent().fadeIn('slow');
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
