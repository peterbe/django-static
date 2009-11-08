/* Example comment */
$(function () {
   
   // Hide all images first
   $('img.peter:visible').hide();
   
   // Example of something silly to do
   setTimeout(function() {
      $('img.peter:hidden').fadeIn("slow");
   }, 2*1000);
   
   
});