window.$ = require("jquery");
import "bootstrap";
import 'bootstrap/dist/css/bootstrap.min.css';
import './style.css'

window.too_old = function() {
  $("#refresh_badge").removeClass("d-none");
  $("#refresh_status").addClass("d-inline");
  $("#summary").removeClass("border-success border-danger");
  $("#summary").addClass("border-warning");
}
