import $ from "jquery";

window.Alpine.data("Hintpoints",()=>({                    
    
    challengevalue: '---',
    async hintpointvalue(id){
        const url = `/api/hintpoint/challengevalue/${id}`;
        const res = await $.get(url)
        this.challengevalue = res.data
        }

}))

window.Alpine.start()