import $ from "jquery";

window.Alpine.data("Hintpoints",()=>({                    
    
    idx: 0,
    challengevalue: '',
    async hintpointvalue(id){
        const url = `/api/hintpoint/challengevalue/${id}`;
        const res = await $.get(url);
        this.challengevalue = res.data;
        idx = id;
    }
}))

window.Alpine.start()