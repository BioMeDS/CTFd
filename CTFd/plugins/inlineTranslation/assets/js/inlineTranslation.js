import $ from "jquery";
import { langPanel } from './lang-panel';

window.customElements.define("lang-panel", langPanel);

//filter out lang-panels 
(async ()=>{
    var found = false

    const lang = document.cookie
        .split(";")
        .find((row)=> row.startsWith("language="))
        ?.split("=")[1];
    console.log(lang)
    $("lang-panel").hide();
    const found_panels = $(`lang-panel[lang=${lang}]`);
    console.log(found_panels);
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
