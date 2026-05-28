import CTFd from "@ctfdio/ctfd-js";
import Alpine from "alpinejs";
import $ from "jquery";
import { langPanel } from './lang-panel';

window.CTFd = CTFd;
window.Alpine = Alpine;

window.customElements.define("lang-panel", langPanel);

//filter out lang-panels 
(async ()=>{
    var found = false

    const lang = document.cookie
        .split(";")
        .find((row)=> row.startsWith("language="))
        ?.split("=")[1];
    $("lang-panel").hide();
    const found_panels = $(`lang-panel[lang=${lang}]`);
    if(found_panels.length > 0){
        found_panels.show();
        found = true;
    }
    if(!found){
        //enable standard language
        $.get("/admin/inlineTranslation/standardlanguage",function(res){
            $(`lang-panel[lang=${res.data}]`).show();
        });
    }
})();

Alpine.start();

