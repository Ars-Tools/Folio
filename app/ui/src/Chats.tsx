import { createSignal, For } from "solid-js";

export default function Chats() {
  const [messages] = createSignal([
    { id: 1, sender: "Bot1", content: "Hello, how can I help you today?", timestamp: "10:00 AM" },
    { id: 2, sender: "You", content: "I need to check the system status.", timestamp: "10:01 AM" },
    { id: 3, sender: "Bot1", content: "The system is currently operational.", timestamp: "10:02 AM" },
  ]);

  return (
    <div class="w-full h-full flex flex-col">
      <h1 class="text-3xl font-bold mb-8">Chats</h1>
      
      <div class="flex-1 bg-neutral-800 rounded-xl border border-neutral-700 flex flex-col overflow-hidden w-full">
        {/* Chat List Placeholder or Active Chat */}
        <div class="flex-1 p-6 overflow-y-auto space-y-4">
             <For each={messages()}>
               {(msg) => (
                 <div class={`flex flex-col ${msg.sender === "You" ? "items-end" : "items-start"}`}>
                   <div class={`px-4 py-2 rounded-lg max-w-md ${
                     msg.sender === "You" 
                       ? "bg-blue-600/20 text-blue-100 border border-blue-600/30" 
                       : "bg-neutral-700 border border-neutral-600"
                   }`}>
                     <div class="text-sm">{msg.content}</div>
                   </div>
                   <div class="text-xs text-neutral-500 mt-1">{msg.timestamp}</div>
                 </div>
               )}
             </For>
        </div>
        
        <div class="p-4 border-t border-neutral-700 bg-neutral-800">
           <div class="flex gap-2">
             <input 
               type="text" 
               placeholder="Type a message..." 
               class="flex-1 bg-neutral-900 border border-neutral-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-neutral-500"
             />
             <button class="bg-neutral-700 hover:bg-neutral-600 px-4 py-2 rounded-lg transition-colors border border-neutral-600">
               Send
             </button>
           </div>
        </div>
      </div>
    </div>
  );
}
