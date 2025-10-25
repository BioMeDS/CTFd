

// just a data structure holding id "lang"
export class langPanel extends HTMLElement{

  static observedAttributes = ["lang"];

  constructor(){
      super();
  }

  connectedCallback() {

    
  }

  disconnectedCallback() {

  }

  connectedMoveCallback() {

  }

  adoptedCallback() {
    
  }

  attributeChangedCallback(name, oldValue, newValue) {
    console.log(`Attribute ${name} has changed.`);
  }
}

