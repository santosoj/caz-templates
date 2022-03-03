import Prompt from 'prompt-sync'

interface Props {
  name: string
  age?: number | string
}

function asdf({name, age}: Props): string {
  return `${name}, ${age || 'would rather not say'}`
}

const prompt = Prompt(undefined)
const name = prompt('What is your name? ')
const age = prompt('What is your age? ')
console.log(asdf({name, age}))
