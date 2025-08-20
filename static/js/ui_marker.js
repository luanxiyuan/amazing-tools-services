$(document).ready(function() {
    // when application_id value was changed and not empty, get the modules and render it in the select element which id == module_id
    $('#application_id').change(function() {
        var application_id = $(this).val();
        if (application_id) {
            $.ajax({
                url: '/ui_marker/get_modules_by_application',
                type: 'GET',
                data: {
                    application_id: application_id
                },
                success: function(response) {
                    var modules = response.modules;
                    var module_id = $('#module_id');
                    module_id.empty();
                    var option = document.createElement('option');
                    option.value = '';
                    option.text = '-Select Module-';
                    module_id.append(option);
                    var function_id = $('#function_id');
                    function_id.empty();
                    var option = document.createElement('option');
                    option.value = '';
                    option.text = '-Select Function-';
                    function_id.append(option);
                    for (var i = 0; i < modules.length; i++) {
                        var option = document.createElement('option');
                        option.value = modules[i].id;
                        option.text = modules[i].name;
                        module_id.append(option);
                    }
                }
            });
        }
    });
    // when module_id values were changed && both application_id and module_id are not empty, get the functions and render it in the select element which id == function_id
    $('#module_id').change(function() {
        var application_id = $('#application_id').val();
        var module_id = $(this).val();
        if (application_id && module_id) {
            $.ajax({
                url: '/ui_marker/get_functions_by_module',
                type: 'GET',
                data: {
                    application_id: application_id,
                    module_id: module_id
                },
                success: function(response) {
                    var functions = response.functions;
                    var function_id = $('#function_id');
                    function_id.empty();
                    var option = document.createElement('option');
                    option.value = '';
                    option.text = '-Select Function-';
                    function_id.append(option);
                    for (var i = 0; i < functions.length; i++) {
                        var option = document.createElement('option');
                        option.value = functions[i].id;
                        option.text = functions[i].name;
                        function_id.append(option);
                    }
                }
            });
        }
    });
    // when search_btn being clicked, check if all the values are not empty, then submit the form
    $('#search_btn').click(function() {
        var application_id = $('#application_id').val();
        var module_id = $('#module_id').val();
        var function_id = $('#function_id').val();
        if (application_id && module_id && function_id) {
            $('#form_page_listing').submit();
        } else {
            return;
        }
    });
});
