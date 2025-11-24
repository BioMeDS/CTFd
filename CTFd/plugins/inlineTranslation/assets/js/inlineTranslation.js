import $ from "jquery";
import { langPanel } from './lang-panel';

window.customElements.define("lang-panel", langPanel);

//filter out lang-panels 
const callback = async ()=>{
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
};

callback();

//challenge view
const observer = new MutationObserver(callback);
const woppy = $("#challenge-window")[0];
if (woppy) {
    observer.observe(woppy,{attributes: true});
}



