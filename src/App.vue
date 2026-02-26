<script>
 export default {
  setup() {
   console.log('setup')
  },
  data() {
    return {
      userName: 'roy',
      sex: '男',
      salary: 1000,
      userInfo: {
        age: 18,
        name: 'roy',
        sex: '男',
        job: '前端',
        salary: 1000,
        department: 'IT',
        skill: ['HTML', 'CSS', 'JS','JAVA']
      }
      ,newSkill:''
    }
  },
  methods: {
    add() {
      console.log(this.userName, this.sex, this.salary)
       this.salary+=1000
    }
   
  }
}
</script>

<template>
  <div class="userInfo">
    姓名：<input type="text" v-model="userName"> {{userName}}</input> <br/>
    性别：<input type="radio" name="sex" value="1" v-model="sex">男</input>
    <input type="radio" name="sex" value="0" v-model="sex">女</input><br/>
    薪水：<input type="number" v-model="salary">{{salary}}</input><br/>
    <button @click="add">提交</button>

    <hr/>

    <div>
      <h2> 个人信息 </h2>
      <p>   年龄 <input type="number" v-model="userInfo.age">{{age}}</input>   </p>
      <p>
        性别 <input type="radio" name="sex" value="1" v-model="userInfo.sex">男</input>
        <input type="radio" name="sex" value="0" v-model="userInfo.sex">女</input>
      </p>
      <p>
        岗位 <select v-model="userInfo.department">
          <option value="1">前端</option>
          <option value="2">后端</option>
        </select>
      </p>
      <p>
        技能 <input type="checkbox" value="1" v-model="userInfo.skill">HTML</input>
        <input type="checkbox" value="2" v-model="userInfo.skill">CSS</input>
        <input type="checkbox" value="3" v-model="userInfo.skill">JS</input>
      </p>
      <p>
        技术 <span v-for="item in userInfo.skill">{{item}}</span>
      </p>
      <p> 新技术 <input v-model="newSkill"/>
        <button @click="userInfo.skill.push(newSkill)">添加</button>
      </p>

      <p>
        个人信息汇总:   {{userInfo}}
      </p>
    </div>
  </div>

</template>

<style scoped>
 .userInfo {
   width: 1000px;
   margin: 0 auto;
   background-attachment: fixed;
   background-color: aqua;
  
 }
 .userInfo span{
   color: red;
   background-color: yellow;
   margin-left: 10px;
   border-radius: 5px;
 }
</style>
