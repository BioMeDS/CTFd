import CTFd from "@ctfdio/ctfd-js";
import $ from "jquery";

CTFd.init(window.init);

$(".toggle-button").click(function() {
    function foo (res) {
        $("#"+res.id).html(res.data)
        if(res.data === "enabled"){
            $("#"+res.id).removeClass("bg-danger").addClass("bg-success")
        }else{
            $("#"+res.id).removeClass("bg-success").addClass("bg-danger")
        }}
    $.get(`/admin/LuaUtils/config/${this.id}`,function(res){
        foo(res)
    })
  });

$("select").on('change',function(){
    CTFd.fetch(`/admin/LuaUtils/config/${this.id}`, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        value: this.value
      }),
    })  
});

$("textarea").on('change',function(){

    $("#"+this.id+"-submit").prop("disabled", false).addClass("bg-success");

});

$(".submit-button").click('change',function(){
    
    const cleaned_id = this.id.replace("-submit","")
    const value = $("#"+cleaned_id).val()

    CTFd.fetch(`/admin/LuaUtils/config/${cleaned_id}`, {
      method: "POST",
        credentials: "same-origin",
        headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        },
        body: JSON.stringify({
        value: value
        }),
    }).then(() => {
        this.disabled = true;
        this.classList.remove("bg-success");
    });
});
$(".reset-button").click(function(){
    CTFd.fetch(`/admin/LuaUtils/config/${this.id.replace("-reset","")}`, {
      method: "POST",
        credentials: "same-origin",
        headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        },
        body: JSON.stringify({
        value: this.value}),
    }).then(
        $("#"+this.id.replace("-reset","")).val(this.value)
    )
});