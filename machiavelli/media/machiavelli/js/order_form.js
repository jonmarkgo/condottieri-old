function toggle_params() {
	var code = $("#id_code").val()
	switch (code) {
		case 'H':
		case 'B':
			$("#id_destination").parent().fadeOut('slow');
			$("#id_type").parent().fadeOut('slow');
			$("#id_subunit").parent().fadeOut('slow');
			$("#id_subcode").parent().fadeOut('slow');
			$("#id_subdestination").parent().fadeOut('slow');
			$("#id_subtype").parent().fadeOut('slow');
			break;
		case '-':
			$("#id_type").parent().fadeOut('slow');
			$("#id_subunit").parent().fadeOut('slow');
			$("#id_subcode").parent().fadeOut('slow');
			$("#id_subdestination").parent().fadeOut('slow');
			$("#id_subtype").parent().fadeOut('slow');
			$("#id_destination").parent().fadeIn('slow');
			
			// If a unit is selected, fetch its destinations
			var unitId = $("#id_unit").val();
			if (unitId) {
				var url = game_url + "/get_destinations/" + unitId + "/";
				console.log("Fetching destinations from:", url);
				$.ajax({
					url: url,
					dataType: 'json',
					success: function(data) {
						console.log("Received data:", data);
						var destinationSelect = $("#id_destination");
						destinationSelect.empty();
						if (data.destinations && data.destinations.length > 0) {
							destinationSelect.append($('<option></option>').val('').text('---------'));
							$.each(data.destinations, function(i, dest) {
								destinationSelect.append($('<option></option>').val(dest.id).text(dest.name));
							});
							destinationSelect.parent().show();
						} else {
							destinationSelect.parent().hide();
						}
					},
					error: function(jqXHR, textStatus, errorThrown) {
						console.error("AJAX request failed:", textStatus, errorThrown);
						console.error("Response:", jqXHR.responseText);
					}
				});
			}
			break;
		case '=':
			$("#id_destination").parent().fadeOut('slow');
			$("#id_subunit").parent().fadeOut('slow');
			$("#id_subcode").parent().fadeOut('slow');
			$("#id_subdestination").parent().fadeOut('slow');
			$("#id_subtype").parent().fadeOut('slow');
			$("#id_type").parent().fadeIn('slow');
			break;
		case 'C':
			$("#id_destination").parent().fadeOut('slow');
			$("#id_type").parent().fadeOut('slow');
			$("#id_subcode").parent().fadeOut('slow');
			$("#id_subtype").parent().fadeOut('slow');
			$("#id_subunit").parent().fadeIn('slow');
			$("#id_subdestination").parent().fadeIn('slow');
			break;
		case 'S':
			$("#id_destination").parent().fadeOut('slow');
			$("#id_type").parent().fadeOut('slow');
			$("#id_subdestination").parent().fadeOut('slow');
			$("#id_subtype").parent().fadeOut('slow');
			$("#id_subunit").parent().fadeIn('slow');
			$("#id_subcode").parent().fadeIn('slow');
			toggle_subparams();
			break;
	}
}

function toggle_subparams() {
	var code = $("#id_subcode").val()
	switch (code) {
		case 'H':
			$("#id_subdestination").parent().fadeOut('slow');
			$("#id_subtype").parent().fadeOut('slow');
			break;
		case '-':
			$("#id_subtype").parent().fadeOut('slow');
			$("#id_subdestination").parent().fadeIn('slow');
			break;
		case '=':
			$("#id_subdestination").parent().fadeOut('slow');
			$("#id_subtype").parent().fadeIn('slow');
			break;
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
	$("#id_code").change( toggle_params );
	$("#id_subcode").change (toggle_subparams );
	$("#id_unit").change( function() {
		// When unit changes, get destinations via AJAX
		var unitId = $(this).val();
		var orderType = $("#id_code").val();
		if (unitId && orderType === '-') {
			var url = game_url + "/get_destinations/" + unitId + "/";
			console.log("Fetching destinations from:", url);
			$.ajax({
				url: url,
				dataType: 'json',
				success: function(data) {
					console.log("Received data:", data);
					var destinationSelect = $("#id_destination");
					destinationSelect.empty();
					if (data.destinations && data.destinations.length > 0) {
						destinationSelect.append($('<option></option>').val('').text('---------'));
						$.each(data.destinations, function(i, dest) {
							destinationSelect.append($('<option></option>').val(dest.id).text(dest.name));
						});
						destinationSelect.parent().show();
					} else {
						destinationSelect.parent().hide();
					}
				},
				error: function(jqXHR, textStatus, errorThrown) {
					console.error("AJAX request failed:", textStatus, errorThrown);
					console.error("Response:", jqXHR.responseText);
				}
			});
		} else {
			$("#id_destination").parent().hide();
		}
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
	
	// If a unit is selected when the page loads, show its destinations only if it's a move order
	if ($("#id_unit").val() && $("#id_code").val() === '-') {
		$("#id_destination").parent().show();
	}
});
