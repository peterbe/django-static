/* Example comment */
$(function () {
   
   // Hide all images first
   $('img:visible').hide();
   
   // Example of something silly to do
   setTimeout(function() {
      $('img:hidden').fadeIn("slow");
   }, 2*1000);
   
   
});