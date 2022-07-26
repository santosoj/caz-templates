const {exec} = require('child_process')

module.exports = {
  prompts: [
  ],
  emit: async ctx => {
    const {dest} = ctx
    await new Promise((resolve, reject) => {
      exec(`chmod +x '${dest}/console.sh'`, function (err, stdout, stderr) {
        if (err) {
          return reject(err)
        }
        resolve()
      })
    })
  },
}
